from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import csv
import io
from app.db import get_conn, init_pool, close_pool
from app.realtime_sync import start_realtime_sync, stop_realtime_sync
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Business Intelligence Service",
    description="Microservicio de Business Intelligence para agencia de viajes con sincronización en tiempo real",
    version="2.0.0"
)


# Evento de inicio: iniciar sincronización en tiempo real
@app.on_event("startup")
async def startup_event():
    """Iniciar la sincronización en tiempo real al arrancar la aplicación"""
    logger.info("🚀 Iniciando aplicación...")
    try:
        # Inicializar pool de Postgres antes de arrancar el worker
        try:
            init_pool(min_size=1, max_size=5)
            logger.info("✅ Pool de PostgreSQL inicializado")
        except Exception as e:
            logger.warning(f"No se pudo inicializar el pool de Postgres: {e}")

        if start_realtime_sync():
            logger.info("✅ Sincronización en tiempo real activada")
        else:
            logger.warning("⚠️ No se pudo activar la sincronización en tiempo real")
    except Exception as e:
        logger.error(f"❌ Error al iniciar sincronización en tiempo real: {e}")


# Evento de cierre: detener sincronización
@app.on_event("shutdown")
async def shutdown_event():
    """Detener la sincronización al cerrar la aplicación"""
    logger.info("⏹️ Deteniendo aplicación...")
    stop_realtime_sync()
    # Cerrar pool de Postgres
    try:
        close_pool()
        logger.info("✅ Pool de PostgreSQL cerrado")
    except Exception as e:
        logger.warning(f"Error cerrando pool de Postgres: {e}")
    logger.info("👋 Aplicación detenida")


# Modelos Pydantic para respuestas
class HealthResponse(BaseModel):
    status: str


class ResumenKPIs(BaseModel):
    total_clientes: int
    total_ventas_confirmadas: int
    total_monto_vendido: float
    tasa_cancelacion: float


class TendenciaDia(BaseModel):
    fecha: str
    cantidad_reservas: int


class TopDestino(BaseModel):
    destino: str
    ingresos: float


class Periodo(BaseModel):
    inicio: Optional[str] = None
    fin: Optional[str] = None


class DashboardResumenResponse(BaseModel):
    periodo: Periodo
    kpis: ResumenKPIs
    top_destinos: List[TopDestino]
    tendencia_reservas_por_dia: List[TendenciaDia]


class MargenBrutoResponse(BaseModel):
    margen_bruto_pct: float
    ingresos: float
    costo: float
    periodo: Periodo


class TasaConversionResponse(BaseModel):
    tasa_conversion_pct: float
    periodo: Periodo


class TasaCancelacionResponse(BaseModel):
    tasa_cancelacion_pct: float
    periodo: Periodo


class CsatPromedioResponse(BaseModel):
    csat_promedio: float
    periodo: Periodo


class TopDestinosResponse(BaseModel):
    destinos: List[TopDestino]
    periodo: Periodo


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Endpoint de salud del servicio.
    Retorna el estado del microservicio.
    """
    return HealthResponse(status="ok")


@app.get("/sync/status", tags=["Health"])
async def sync_status():
    """
    Endpoint para verificar el estado de la sincronización en tiempo real.
    Retorna si la sincronización está activa o no.
    """
    from app.realtime_sync import realtime_sync
    return {
        "sync_enabled": True,
        "sync_running": realtime_sync.is_running,
        "message": "Sincronización en tiempo real activa" if realtime_sync.is_running else "Sincronización no activa"
    }


@app.post("/sync/restart", tags=["Health"])
async def restart_sync():
    """
    Endpoint para reiniciar manualmente la sincronización en tiempo real.
    Útil si la sincronización se detiene por algún motivo.
    """
    import time
    try:
        logger.info("🔄 Reiniciando sincronización...")
        stop_realtime_sync()
        time.sleep(2)
        if start_realtime_sync():
            logger.info("✅ Sincronización reiniciada exitosamente")
            return {
                "status": "success",
                "message": "Sincronización reiniciada exitosamente"
            }
        else:
            logger.error("❌ No se pudo reiniciar la sincronización")
            return {
                "status": "error",
                "message": "No se pudo reiniciar la sincronización"
            }
    except Exception as e:
        logger.error(f"❌ Error al reiniciar sincronización: {e}")
        return {
            "status": "error",
            "message": f"Error al reiniciar: {str(e)}"
        }


@app.post("/sync/once", tags=["Health"])
async def sync_once():
    """
    Endpoint para ejecutar UNA sincronización completa manualmente.
    Sincroniza TODOS los datos de MongoDB a PostgreSQL, no solo los cambios nuevos.
    Útil para recuperar datos que se agregaron antes de iniciar el change stream.
    """
    from app.etl import sync_data
    try:
        logger.info("🔄 Ejecutando sincronización manual completa...")
        sync_data()
        logger.info("✅ Sincronización manual completada")
        return {
            "status": "success",
            "message": "Sincronización manual completada exitosamente"
        }
    except Exception as e:
        logger.error(f"❌ Error en sincronización manual: {e}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


@app.get("/debug/mongo-counts", tags=["Debug"])
async def get_mongo_counts():
    """
    Endpoint de debug para ver cuántos documentos hay en cada colección de MongoDB.
    Compara MongoDB (origen) vs PostgreSQL (destino) para detectar desfases.
    """
    import os
    from pymongo import MongoClient
    
    try:
        # Conectar a MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
        
        if not mongo_uri:
            raise ValueError("MONGO_URI no configurada")
        
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mongo_db_name]
        
        # Contar documentos en cada colección
        mongo_counts = {
            "clientes": mongo_db.clientes.count_documents({}),
            "agentes": mongo_db.agentes.count_documents({}),
            "servicios": mongo_db.servicios.count_documents({}),
            "paquetes_turisticos": mongo_db.paquetesTuristicos.count_documents({}),
            "ventas": mongo_db.ventas.count_documents({}),
            "detalle_venta": mongo_db.detalleVenta.count_documents({})
        }
        
        # Contar registros en PostgreSQL
        postgres_counts = {}
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM clientes")
                postgres_counts["clientes"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM agentes")
                postgres_counts["agentes"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM servicios")
                postgres_counts["servicios"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM paquetes_turisticos")
                postgres_counts["paquetes_turisticos"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM ventas")
                postgres_counts["ventas"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM detalle_venta")
                postgres_counts["detalle_venta"] = cur.fetchone()[0]
        
        mongo_client.close()
        
        # Calcular diferencias
        differences = {}
        for collection in mongo_counts:
            diff = mongo_counts[collection] - postgres_counts.get(collection, 0)
            differences[collection] = {
                "mongo": mongo_counts[collection],
                "postgres": postgres_counts.get(collection, 0),
                "diferencia": diff,
                "sincronizado": diff == 0
            }
        
        return {
            "status": "success",
            "database": mongo_db_name,
            "collections": differences,
            "resumen": {
                "total_mongo": sum(mongo_counts.values()),
                "total_postgres": sum(postgres_counts.values()),
                "tablas_sincronizadas": sum(1 for d in differences.values() if d["sincronizado"])
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error al obtener conteos: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/dashboard/resumen", response_model=DashboardResumenResponse, tags=["Dashboard"])
async def obtener_resumen_dashboard(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> DashboardResumenResponse:
    """
    Endpoint para obtener el resumen de KPIs del dashboard.
    Retorna datos reales desde PostgreSQL:
    - Total de clientes
    - Total de ventas confirmadas
    - Total de monto vendido
    - Tasa de cancelación
    
    Parámetros opcionales:
    - fecha_inicio: Fecha de inicio para filtrar ventas (formato: YYYY-MM-DD)
    - fecha_fin: Fecha de fin para filtrar ventas (formato: YYYY-MM-DD)
    """
    try:
        # Construir cláusula WHERE condicionalmente
        where_clause = ""
        params = []
        
        if fecha_inicio is not None and fecha_fin is not None:
            where_clause = "WHERE fecha_venta BETWEEN %s AND %s"
            params = [fecha_inicio, fecha_fin]
        elif fecha_inicio is not None:
            where_clause = "WHERE fecha_venta >= %s"
            params = [fecha_inicio]
        elif fecha_fin is not None:
            where_clause = "WHERE fecha_venta <= %s"
            params = [fecha_fin]
        
        # Construir cláusula WHERE para ventas (usada en múltiples queries)
        ventas_where = where_clause.replace("fecha_venta", "v.fecha_venta") if where_clause else ""
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Total de clientes (no se filtra por fecha)
                cur.execute("SELECT COUNT(*) FROM clientes")
                total_clientes = cur.fetchone()[0]
                
                # Total de ventas confirmadas
                query_ventas_confirmadas = f"""
                    SELECT COUNT(*) 
                    FROM ventas v
                    {ventas_where if ventas_where else "WHERE v.estado = 'confirmada'"}
                    {f"AND v.estado = 'confirmada'" if ventas_where else ""}
                """
                if ventas_where:
                    cur.execute(query_ventas_confirmadas, params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'confirmada'")
                total_ventas_confirmadas = cur.fetchone()[0]
                
                # Total de monto vendido (suma de montos de ventas confirmadas)
                query_monto = f"""
                    SELECT COALESCE(SUM(monto), 0) 
                    FROM ventas v
                    {ventas_where if ventas_where else "WHERE v.estado = 'confirmada'"}
                    {f"AND v.estado = 'confirmada'" if ventas_where else ""}
                """
                if ventas_where:
                    cur.execute(query_monto, params)
                else:
                    cur.execute("""
                        SELECT COALESCE(SUM(monto), 0) 
                        FROM ventas 
                        WHERE estado = 'confirmada'
                    """)
                total_monto_vendido = cur.fetchone()[0] or 0.0
                
                # Total de ventas (confirmadas + canceladas) para calcular tasa
                query_total_ventas = f"""
                    SELECT COUNT(*) 
                    FROM ventas v
                    {ventas_where}
                """
                if ventas_where:
                    cur.execute(query_total_ventas, params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas")
                total_ventas = cur.fetchone()[0]
                
                # Total de ventas canceladas
                query_ventas_canceladas = f"""
                    SELECT COUNT(*) 
                    FROM ventas v
                    {ventas_where if ventas_where else "WHERE v.estado = 'cancelada'"}
                    {f"AND v.estado = 'cancelada'" if ventas_where else ""}
                """
                if ventas_where:
                    cur.execute(query_ventas_canceladas, params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'cancelada'")
                total_ventas_canceladas = cur.fetchone()[0]
                
                # Calcular tasa de cancelación usando NULLIF para prevenir división por cero
                query_tasa = f"""
                    SELECT COALESCE(
                        (COUNT(CASE WHEN v.estado = 'cancelada' THEN 1 END)::DECIMAL / 
                         NULLIF(COUNT(*), 0)) * 100, 
                        0
                    )
                    FROM ventas v
                    {ventas_where}
                """
                if ventas_where:
                    cur.execute(query_tasa, params)
                else:
                    cur.execute("""
                        SELECT COALESCE(
                            (COUNT(CASE WHEN estado = 'cancelada' THEN 1 END)::DECIMAL / 
                             NULLIF(COUNT(*), 0)) * 100, 
                            0
                        )
                        FROM ventas
                    """)
                tasa_cancelacion = float(cur.fetchone()[0] or 0.0)
                
                # Obtener top destinos (top 5 por defecto)
                fecha_where_top = ""
                params_top = []
                if fecha_inicio is not None and fecha_fin is not None:
                    fecha_where_top = "AND v.fecha_venta BETWEEN %s AND %s"
                    params_top = [fecha_inicio, fecha_fin]
                elif fecha_inicio is not None:
                    fecha_where_top = "AND v.fecha_venta >= %s"
                    params_top = [fecha_inicio]
                elif fecha_fin is not None:
                    fecha_where_top = "AND v.fecha_venta <= %s"
                    params_top = [fecha_fin]
                
                query_top_destinos = f"""
                    SELECT 
                        COALESCE(s.destino_ciudad, pt.destino_principal, 'Sin destino') as destino,
                        COALESCE(SUM(dv.subtotal), 0) as ingresos
                    FROM detalle_venta dv
                    INNER JOIN ventas v ON dv.venta_id = v.id
                    LEFT JOIN servicios s ON dv.servicio_id = s.id
                    LEFT JOIN paquetes_turisticos pt ON dv.paquete_id = pt.id
                    WHERE v.estado = 'confirmada'
                    {fecha_where_top}
                    GROUP BY COALESCE(s.destino_ciudad, pt.destino_principal, 'Sin destino')
                    HAVING COALESCE(SUM(dv.subtotal), 0) > 0
                    ORDER BY ingresos DESC
                    LIMIT 5
                """
                cur.execute(query_top_destinos, params_top)
                
                top_destinos_results = cur.fetchall()
                top_destinos = [
                    TopDestino(
                        destino=row[0] or "Sin destino",
                        ingresos=round(float(row[1] or 0.0), 2)
                    )
                    for row in top_destinos_results
                ]
                
                # Obtener tendencia de reservas por día
                fecha_where_tendencia = ""
                params_tendencia = []
                if fecha_inicio is not None and fecha_fin is not None:
                    fecha_where_tendencia = "AND v.fecha_venta BETWEEN %s AND %s"
                    params_tendencia = [fecha_inicio, fecha_fin]
                elif fecha_inicio is not None:
                    fecha_where_tendencia = "AND v.fecha_venta >= %s"
                    params_tendencia = [fecha_inicio]
                elif fecha_fin is not None:
                    fecha_where_tendencia = "AND v.fecha_venta <= %s"
                    params_tendencia = [fecha_fin]
                
                query_tendencia = f"""
                    SELECT 
                        DATE(fecha_venta) as fecha,
                        COUNT(*) as cantidad_reservas
                    FROM ventas v
                    WHERE v.estado = 'confirmada'
                    {fecha_where_tendencia}
                    GROUP BY DATE(fecha_venta)
                    ORDER BY fecha ASC
                """
                cur.execute(query_tendencia, params_tendencia)
                
                tendencia_results = cur.fetchall()
                tendencia_reservas_por_dia = [
                    TendenciaDia(
                        fecha=row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                        cantidad_reservas=int(row[1] or 0)
                    )
                    for row in tendencia_results
                ]
        
        # Preparar período para la respuesta
        periodo = Periodo(
            inicio=fecha_inicio.isoformat() if fecha_inicio else None,
            fin=fecha_fin.isoformat() if fecha_fin else None
        )
        
        kpis = ResumenKPIs(
            total_clientes=total_clientes,
            total_ventas_confirmadas=total_ventas_confirmadas,
            total_monto_vendido=float(total_monto_vendido),
            tasa_cancelacion=round(tasa_cancelacion, 2)
        )
        
        return DashboardResumenResponse(
            periodo=periodo,
            kpis=kpis,
            top_destinos=top_destinos,
            tendencia_reservas_por_dia=tendencia_reservas_por_dia
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener datos del dashboard: {str(e)}"
        )


@app.get("/kpi/margen-bruto", response_model=MargenBrutoResponse, tags=["KPI"])
async def obtener_margen_bruto(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> MargenBrutoResponse:
    """
    Endpoint para calcular el margen bruto de las ventas confirmadas.
    
    Considera solo ventas confirmadas.
    - Ingresos: SUM(detalle_venta.subtotal)
    - Costo: Si hay servicio_id, usa servicios.precio_costo * cantidad
             Si hay paquete_id, usa paquetes_turisticos.precio_total_venta * 0.75
    - Margen bruto %: (SUM(ingresos - costo) / NULLIF(SUM(ingresos), 0)) * 100
    
    Parámetros opcionales:
    - fecha_inicio: Fecha de inicio para filtrar ventas (formato: YYYY-MM-DD)
    - fecha_fin: Fecha de fin para filtrar ventas (formato: YYYY-MM-DD)
    """
    try:
        # Construir cláusula WHERE para filtrar por fechas
        fecha_where = ""
        params = []
        
        if fecha_inicio is not None and fecha_fin is not None:
            fecha_where = "AND v.fecha_venta BETWEEN %s AND %s"
            params = [fecha_inicio, fecha_fin]
        elif fecha_inicio is not None:
            fecha_where = "AND v.fecha_venta >= %s"
            params = [fecha_inicio]
        elif fecha_fin is not None:
            fecha_where = "AND v.fecha_venta <= %s"
            params = [fecha_fin]
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Query para calcular ingresos, costos y margen bruto
                # Usa LEFT JOINs para servicios y paquetes_turisticos
                # Calcula el costo basado en servicio_id o paquete_id
                query = f"""
                    SELECT 
                        COALESCE(SUM(dv.subtotal), 0) as ingresos,
                        COALESCE(SUM(
                            CASE 
                                WHEN dv.servicio_id IS NOT NULL THEN 
                                    COALESCE(s.precio_costo, 0) * dv.cantidad
                                WHEN dv.paquete_id IS NOT NULL THEN 
                                    COALESCE(pt.precio_total_venta, 0) * 0.75 * dv.cantidad
                                ELSE 0
                            END
                        ), 0) as costo,
                        COALESCE(
                            ((SUM(dv.subtotal) - SUM(
                                CASE 
                                    WHEN dv.servicio_id IS NOT NULL THEN 
                                        COALESCE(s.precio_costo, 0) * dv.cantidad
                                    WHEN dv.paquete_id IS NOT NULL THEN 
                                        COALESCE(pt.precio_total_venta, 0) * 0.75 * dv.cantidad
                                    ELSE 0
                                END
                            )) / NULLIF(SUM(dv.subtotal), 0)) * 100,
                            0
                        ) as margen_bruto_pct
                    FROM detalle_venta dv
                    INNER JOIN ventas v ON dv.venta_id = v.id
                    LEFT JOIN servicios s ON dv.servicio_id = s.id
                    LEFT JOIN paquetes_turisticos pt ON dv.paquete_id = pt.id
                    WHERE v.estado = 'confirmada'
                    {fecha_where}
                """
                
                cur.execute(query, params)
                result = cur.fetchone()
                
                ingresos = float(result[0] or 0.0)
                costo = float(result[1] or 0.0)
                margen_bruto_pct = float(result[2] or 0.0)
        
        # Preparar período para la respuesta
        periodo = Periodo(
            inicio=fecha_inicio.isoformat() if fecha_inicio else None,
            fin=fecha_fin.isoformat() if fecha_fin else None
        )
        
        return MargenBrutoResponse(
            margen_bruto_pct=round(margen_bruto_pct, 2),
            ingresos=round(ingresos, 2),
            costo=round(costo, 2),
            periodo=periodo
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular el margen bruto: {str(e)}"
        )


@app.get("/kpi/tasa-conversion", response_model=TasaConversionResponse, tags=["KPI"])
async def obtener_tasa_conversion(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> TasaConversionResponse:
    """
    Endpoint para calcular la tasa de conversión de ventas.
    
    Tasa de conversión = (ventas confirmadas / total de ventas) * 100
    Si existe el estado "emitida", se usa en lugar de "confirmada".
    
    Filtra por fecha_venta si se proporcionan fechas.
    
    Parámetros opcionales:
    - fecha_inicio: Fecha de inicio para filtrar ventas (formato: YYYY-MM-DD)
    - fecha_fin: Fecha de fin para filtrar ventas (formato: YYYY-MM-DD)
    """
    try:
        # Construir cláusula WHERE para filtrar por fechas
        fecha_where = ""
        params = []
        
        if fecha_inicio is not None and fecha_fin is not None:
            fecha_where = "WHERE fecha_venta BETWEEN %s AND %s"
            params = [fecha_inicio, fecha_fin]
        elif fecha_inicio is not None:
            fecha_where = "WHERE fecha_venta >= %s"
            params = [fecha_inicio]
        elif fecha_fin is not None:
            fecha_where = "WHERE fecha_venta <= %s"
            params = [fecha_fin]
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Verificar si existe el estado "emitida"
                cur.execute("""
                    SELECT DISTINCT estado 
                    FROM ventas 
                    LIMIT 10
                """)
                estados = [row[0] for row in cur.fetchall()]
                estado_confirmado = "emitida" if "emitida" in estados else "confirmada"
                
                # Calcular tasa de conversión usando NULLIF para prevenir división por cero
                if fecha_where:
                    query = f"""
                        SELECT COALESCE(
                            (COUNT(CASE WHEN estado = %s THEN 1 END)::DECIMAL / 
                             NULLIF(COUNT(*), 0)) * 100,
                            0
                        ) as tasa_conversion
                        FROM ventas
                        {fecha_where}
                    """
                    query_params = [estado_confirmado] + params
                else:
                    query = """
                        SELECT COALESCE(
                            (COUNT(CASE WHEN estado = %s THEN 1 END)::DECIMAL / 
                             NULLIF(COUNT(*), 0)) * 100,
                            0
                        ) as tasa_conversion
                        FROM ventas
                    """
                    query_params = [estado_confirmado]
                
                cur.execute(query, query_params)
                tasa_conversion = float(cur.fetchone()[0] or 0.0)
        
        # Preparar período para la respuesta
        periodo = Periodo(
            inicio=fecha_inicio.isoformat() if fecha_inicio else None,
            fin=fecha_fin.isoformat() if fecha_fin else None
        )
        
        return TasaConversionResponse(
            tasa_conversion_pct=round(tasa_conversion, 2),
            periodo=periodo
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular la tasa de conversión: {str(e)}"
        )


@app.get("/kpi/tasa-cancelacion", response_model=TasaCancelacionResponse, tags=["KPI"])
async def obtener_tasa_cancelacion(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> TasaCancelacionResponse:
    """
    Endpoint para calcular la tasa de cancelación de ventas.
    
    Tasa de cancelación = (ventas canceladas / total de ventas) * 100
    
    Filtra por fecha_venta si se proporcionan fechas.
    
    Parámetros opcionales:
    - fecha_inicio: Fecha de inicio para filtrar ventas (formato: YYYY-MM-DD)
    - fecha_fin: Fecha de fin para filtrar ventas (formato: YYYY-MM-DD)
    """
    try:
        # Construir cláusula WHERE para filtrar por fechas
        fecha_where = ""
        params = []
        
        if fecha_inicio is not None and fecha_fin is not None:
            fecha_where = "WHERE fecha_venta BETWEEN %s AND %s"
            params = [fecha_inicio, fecha_fin]
        elif fecha_inicio is not None:
            fecha_where = "WHERE fecha_venta >= %s"
            params = [fecha_inicio]
        elif fecha_fin is not None:
            fecha_where = "WHERE fecha_venta <= %s"
            params = [fecha_fin]
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Calcular tasa de cancelación usando NULLIF para prevenir división por cero
                query = f"""
                    SELECT COALESCE(
                        (COUNT(CASE WHEN estado = 'cancelada' THEN 1 END)::DECIMAL / 
                         NULLIF(COUNT(*), 0)) * 100,
                        0
                    ) as tasa_cancelacion
                    FROM ventas
                    {fecha_where}
                """
                
                cur.execute(query, params)
                tasa_cancelacion = float(cur.fetchone()[0] or 0.0)
        
        # Preparar período para la respuesta
        periodo = Periodo(
            inicio=fecha_inicio.isoformat() if fecha_inicio else None,
            fin=fecha_fin.isoformat() if fecha_fin else None
        )
        
        return TasaCancelacionResponse(
            tasa_cancelacion_pct=round(tasa_cancelacion, 2),
            periodo=periodo
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular la tasa de cancelación: {str(e)}"
        )


@app.get("/kpi/csat-promedio", response_model=CsatPromedioResponse, tags=["KPI"])
async def obtener_csat_promedio(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> CsatPromedioResponse:
    """
    Endpoint para calcular el promedio de satisfacción del cliente (CSAT).
    
    Calcula el promedio de ventas.puntuacion_satisfaccion
    Solo considera ventas con estado "confirmada" o "finalizada".
    Filtra por fecha_venta si se proporcionan fechas.
    
    Parámetros opcionales:
    - fecha_inicio: Fecha de inicio para filtrar ventas (formato: YYYY-MM-DD)
    - fecha_fin: Fecha de fin para filtrar ventas (formato: YYYY-MM-DD)
    """
    try:
        # Construir cláusula WHERE para filtrar por fechas
        fecha_where = ""
        params = []
        
        if fecha_inicio is not None and fecha_fin is not None:
            fecha_where = "AND fecha_venta BETWEEN %s AND %s"
            params = [fecha_inicio, fecha_fin]
        elif fecha_inicio is not None:
            fecha_where = "AND fecha_venta >= %s"
            params = [fecha_inicio]
        elif fecha_fin is not None:
            fecha_where = "AND fecha_venta <= %s"
            params = [fecha_fin]
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Calcular promedio de puntuación de satisfacción
                # Solo ventas confirmadas o finalizadas
                query = f"""
                    SELECT COALESCE(AVG(puntuacion_satisfaccion), 0) as csat_promedio
                    FROM ventas
                    WHERE estado IN ('confirmada', 'finalizada')
                      AND puntuacion_satisfaccion IS NOT NULL
                    {fecha_where}
                """
                
                cur.execute(query, params)
                csat_promedio = float(cur.fetchone()[0] or 0.0)
        
        # Preparar período para la respuesta
        periodo = Periodo(
            inicio=fecha_inicio.isoformat() if fecha_inicio else None,
            fin=fecha_fin.isoformat() if fecha_fin else None
        )
        
        return CsatPromedioResponse(
            csat_promedio=round(csat_promedio, 2),
            periodo=periodo
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular el CSAT promedio: {str(e)}"
        )


@app.get("/analytics/top-destinos", response_model=TopDestinosResponse, tags=["Analytics"])
async def obtener_top_destinos(
    limit: int = 5,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> TopDestinosResponse:
    """
    Endpoint para obtener los destinos más populares por ingresos.
    
    Agrupa por destino usando COALESCE(servicios.destino_ciudad, paquetes_turisticos.destino_principal)
    Suma los ingresos de detalle_venta.subtotal
    Ordena descendente por ingresos
    Filtra por fecha_venta si se proporcionan fechas
    Solo considera ventas confirmadas
    
    Parámetros:
    - limit: Número de destinos a retornar (por defecto: 5)
    - fecha_inicio: Fecha de inicio para filtrar ventas (formato: YYYY-MM-DD)
    - fecha_fin: Fecha de fin para filtrar ventas (formato: YYYY-MM-DD)
    """
    try:
        # Construir cláusula WHERE para filtrar por fechas
        fecha_where = ""
        params = []
        
        if fecha_inicio is not None and fecha_fin is not None:
            fecha_where = "AND v.fecha_venta BETWEEN %s AND %s"
            params = [fecha_inicio, fecha_fin]
        elif fecha_inicio is not None:
            fecha_where = "AND v.fecha_venta >= %s"
            params = [fecha_inicio]
        elif fecha_fin is not None:
            fecha_where = "AND v.fecha_venta <= %s"
            params = [fecha_fin]
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Query para obtener top destinos agrupados por destino
                query = f"""
                    SELECT 
                        COALESCE(s.destino_ciudad, pt.destino_principal, 'Sin destino') as destino,
                        COALESCE(SUM(dv.subtotal), 0) as ingresos
                    FROM detalle_venta dv
                    INNER JOIN ventas v ON dv.venta_id = v.id
                    LEFT JOIN servicios s ON dv.servicio_id = s.id
                    LEFT JOIN paquetes_turisticos pt ON dv.paquete_id = pt.id
                    WHERE v.estado = 'confirmada'
                    {fecha_where}
                    GROUP BY COALESCE(s.destino_ciudad, pt.destino_principal, 'Sin destino')
                    HAVING COALESCE(SUM(dv.subtotal), 0) > 0
                    ORDER BY ingresos DESC
                    LIMIT %s
                """
                
                query_params = params + [limit]
                cur.execute(query, query_params)
                results = cur.fetchall()
                
                destinos = [
                    TopDestino(
                        destino=row[0] or "Sin destino",
                        ingresos=round(float(row[1] or 0.0), 2)
                    )
                    for row in results
                ]
        
        # Preparar período para la respuesta
        periodo = Periodo(
            inicio=fecha_inicio.isoformat() if fecha_inicio else None,
            fin=fecha_fin.isoformat() if fecha_fin else None
        )
        
        return TopDestinosResponse(
            destinos=destinos,
            periodo=periodo
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener top destinos: {str(e)}"
        )


@app.get("/export/ventas.csv", tags=["Export"])
async def exportar_ventas_csv(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
):
    """
    Endpoint para exportar ventas confirmadas a formato CSV.
    
    Selecciona ventas confirmadas uniendo con detalle_venta, servicios y paquetes_turisticos.
    Columnas exportadas:
    - venta_id
    - fecha_venta
    - cliente_id
    - agente_id
    - estado_venta
    - monto_total
    - destino
    - cantidad
    - precio_unitario_venta
    - subtotal
    
    Parámetros opcionales:
    - fecha_inicio: Fecha de inicio para filtrar ventas (formato: YYYY-MM-DD)
    - fecha_fin: Fecha de fin para filtrar ventas (formato: YYYY-MM-DD)
    """
    try:
        # Construir cláusula WHERE para filtrar por fechas
        fecha_where = ""
        params = []
        
        if fecha_inicio is not None and fecha_fin is not None:
            fecha_where = "AND v.fecha_venta BETWEEN %s AND %s"
            params = [fecha_inicio, fecha_fin]
        elif fecha_inicio is not None:
            fecha_where = "AND v.fecha_venta >= %s"
            params = [fecha_inicio]
        elif fecha_fin is not None:
            fecha_where = "AND v.fecha_venta <= %s"
            params = [fecha_fin]
        
        # Query para obtener las ventas con todas las columnas requeridas
        query = f"""
            SELECT 
                v.id as venta_id,
                v.fecha_venta,
                v.cliente_id,
                v.agente_id,
                v.estado as estado_venta,
                v.monto as monto_total,
                COALESCE(s.destino_ciudad, pt.destino_principal, 'Sin destino') as destino,
                dv.cantidad,
                dv.precio_unitario as precio_unitario_venta,
                dv.subtotal
            FROM ventas v
            INNER JOIN detalle_venta dv ON v.id = dv.venta_id
            LEFT JOIN servicios s ON dv.servicio_id = s.id
            LEFT JOIN paquetes_turisticos pt ON dv.paquete_id = pt.id
            WHERE v.estado = 'confirmada'
            {fecha_where}
            ORDER BY v.fecha_venta DESC, v.id
        """
        
        def generate_csv():
            """Generador para crear el CSV en streaming"""
            with get_conn() as conn:
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Escribir cabeceras
                writer.writerow([
                    'venta_id',
                    'fecha_venta',
                    'cliente_id',
                    'agente_id',
                    'estado_venta',
                    'monto_total',
                    'destino',
                    'cantidad',
                    'precio_unitario_venta',
                    'subtotal'
                ])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
                
                # Ejecutar query y escribir filas
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    
                    for row in cur:
                        writer.writerow([
                            row[0] or '',  # venta_id
                            row[1].isoformat() if row[1] else '',  # fecha_venta
                            row[2] or '',  # cliente_id
                            row[3] or '',  # agente_id
                            row[4] or '',  # estado_venta
                            float(row[5]) if row[5] is not None else 0.0,  # monto_total
                            row[6] or 'Sin destino',  # destino
                            row[7] or 0,  # cantidad
                            float(row[8]) if row[8] is not None else 0.0,  # precio_unitario_venta
                            float(row[9]) if row[9] is not None else 0.0  # subtotal
                        ])
                        yield output.getvalue()
                        output.seek(0)
                        output.truncate(0)
        
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="ventas.csv"'
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar ventas a CSV: {str(e)}"
        )


@app.get("/debug/detailed-sync", tags=["Debug"])
async def detailed_sync_debug():
    """
    Endpoint de diagnóstico detallado para ver exactamente qué está pasando
    con la sincronización de datos.
    """
    import os
    from pymongo import MongoClient
    from app.etl import extract_collection, map_cliente
    
    try:
        results = {}
        
        # 1. Verificar MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
        
        if not mongo_uri:
            raise ValueError("MONGO_URI no configurada")
        
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mongo_db_name]
        
        # Extraer clientes de MongoDB
        clientes_mongo = extract_collection(mongo_db, "clientes")
        results["mongo_clientes_extraidos"] = len(clientes_mongo)
        results["mongo_primer_cliente"] = clientes_mongo[0] if clientes_mongo else None
        
        # Transformar el primer cliente
        if clientes_mongo:
            primer_cliente_transformado = map_cliente(clientes_mongo[0])
            results["primer_cliente_transformado"] = primer_cliente_transformado
        
        # 2. Verificar PostgreSQL
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Contar clientes
                cur.execute("SELECT COUNT(*) FROM clientes")
                count = cur.fetchone()[0]
                results["postgres_clientes_count"] = count
                
                # Obtener primeros 3 clientes si existen
                cur.execute("SELECT origen_id, nombre, email FROM clientes LIMIT 3")
                clientes_pg = cur.fetchall()
                results["postgres_primeros_clientes"] = [
                    {"origen_id": c[0], "nombre": c[1], "email": c[2]} 
                    for c in clientes_pg
                ]
                
                # Verificar estructura de la tabla
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'clientes'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                results["postgres_tabla_estructura"] = [
                    {"columna": c[0], "tipo": c[1]} 
                    for c in columns
                ]
        
        mongo_client.close()
        
        return {
            "status": "success",
            "diagnostico": results
        }
        
    except Exception as e:
        logger.error(f"❌ Error en diagnóstico detallado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/debug/test-insert", tags=["Debug"])
async def test_insert_cliente():
    """
    Intenta insertar un cliente de prueba directamente para ver errores específicos.
    """
    import os
    from pymongo import MongoClient
    from app.etl import extract_collection, map_cliente, upsert_clientes
    
    try:
        # Conectar a MongoDB y obtener un cliente real
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
        
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mongo_db_name]
        
        clientes_mongo = extract_collection(mongo_db, "clientes")
        mongo_client.close()
        
        if not clientes_mongo:
            return {"status": "error", "message": "No hay clientes en MongoDB"}
        
        # Transformar primer cliente
        primer_cliente = map_cliente(clientes_mongo[0])
        
        # Intentar insertar en PostgreSQL
        with get_conn() as conn:
            # Deshabilitar autocommit para manejar la transacción
            conn.autocommit = False
            
            try:
                insertados, actualizados = upsert_clientes(conn, [primer_cliente])
                conn.commit()
                
                # Verificar si se insertó
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM clientes WHERE origen_id = %s", (primer_cliente['origen_id'],))
                    count = cur.fetchone()[0]
                
                return {
                    "status": "success",
                    "cliente_mongo": clientes_mongo[0],
                    "cliente_transformado": primer_cliente,
                    "insertados": insertados,
                    "actualizados": actualizados,
                    "verificacion_count": count
                }
                
            except Exception as e:
                conn.rollback()
                logger.error(f"❌ Error al insertar cliente de prueba: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error SQL: {str(e)}")
        
    except Exception as e:
        logger.error(f"❌ Error general en test insert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/debug/simple-check", tags=["Debug"])
async def simple_check():
    """
    Verificación simple: cuántos clientes hay en MongoDB vs PostgreSQL.
    """
    import os
    from pymongo import MongoClient
    import psycopg
    
    try:
        results = {}
        
        # MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mongo_db_name]
        mongo_count = mongo_db.clientes.count_documents({})
        mongo_client.close()
        results["mongodb_clientes"] = mongo_count
        
        # PostgreSQL - usando conexión directa
        database = os.getenv("PG_DATABASE", os.getenv("dbname", "postgres"))
        user = os.getenv("PG_USER", os.getenv("user"))
        password = os.getenv("PG_PASSWORD", os.getenv("password"))
        host = os.getenv("PG_HOST", os.getenv("host", "aws-1-us-east-2.pooler.supabase.com"))
        port = os.getenv("PG_PORT", os.getenv("port", "6543"))
        sslmode = os.getenv("PG_SSLMODE", "require")
        conninfo = f"dbname={database} user={user} password={password} host={host} port={port} sslmode={sslmode}"
        
        conn = psycopg.connect(conninfo)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clientes")
            pg_count = cur.fetchone()[0]
        conn.close()
        results["postgres_clientes"] = pg_count
        
        results["sincronizado"] = mongo_count == pg_count
        results["diferencia"] = mongo_count - pg_count
        
        return {
            "status": "success",
            "data": results
        }
        
    except Exception as e:
        logger.error(f"❌ Error en simple check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
