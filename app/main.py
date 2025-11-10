"""
API REST de Business Intelligence para agencia de viajes.
Proporciona endpoints de KPIs, analytics y sincronización en tiempo real desde MongoDB.
"""
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
    total_ventas_pendientes: int
    total_ventas_canceladas: int
    total_ventas: int
    total_monto_vendido: float
    total_monto_pendiente: float
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


@app.get("/health/pool", tags=["Health"])
async def health_check_pool():
    """
    Endpoint de diagnóstico del pool de conexiones.
    Retorna información sobre el estado del pool.
    """
    from app.db import _POOL
    try:
        if _POOL is None:
            return {
                "pool_status": "not_initialized",
                "message": "Pool no está inicializado",
                "test_connection": "attempting_direct_connection"
            }
        
        # Intentar obtener stats del pool (psycopg_pool)
        pool_info = {
            "pool_status": "initialized",
            "pool_size": _POOL.size if hasattr(_POOL, 'size') else "unknown",
            "max_size": _POOL.max_size if hasattr(_POOL, 'max_size') else "unknown",
            "min_size": _POOL.min_size if hasattr(_POOL, 'min_size') else "unknown"
        }
        
        # Probar obtener una conexión del pool
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    pool_info["test_query"] = "success"
                    pool_info["test_result"] = result[0] if result else None
        except Exception as e:
            pool_info["test_query"] = "failed"
            pool_info["test_error"] = str(e)
        
        return pool_info
        
    except Exception as e:
        return {
            "pool_status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }


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


@app.post("/sync/force", tags=["Health"])
async def force_sync():
    """
    Endpoint para forzar sincronización inmediata.
    Llama a este endpoint después de cambiar el estado de una venta en el frontend.
    """
    from app.etl import sync_data
    try:
        logger.info("⚡ Forzando sincronización inmediata...")
        sync_data()
        logger.info("✅ Sincronización forzada completada")
        return {
            "status": "success",
            "message": "Sincronización forzada completada exitosamente"
        }
    except Exception as e:
        logger.error(f"❌ Error en sincronización forzada: {e}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


@app.get("/debug/ventas-estados", tags=["Debug"])
async def get_ventas_estados():
    """
    Endpoint de debug para ver todas las ventas y sus estados en PostgreSQL.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id, 
                        estado, 
                        monto, 
                        fecha_venta,
                        origen_id
                    FROM ventas
                    ORDER BY fecha_venta DESC
                """)
                
                ventas = []
                for row in cur.fetchall():
                    ventas.append({
                        "id": row[0],
                        "estado": row[1],
                        "monto": float(row[2]) if row[2] else 0.0,
                        "fecha_venta": row[3].isoformat() if row[3] else None,
                        "origen_id": row[4]
                    })
                
                # Contar por estado
                cur.execute("""
                    SELECT estado, COUNT(*), SUM(monto)
                    FROM ventas
                    GROUP BY estado
                    ORDER BY COUNT(*) DESC
                """)
                
                resumen_estados = []
                for row in cur.fetchall():
                    resumen_estados.append({
                        "estado": row[0] or "NULL",
                        "cantidad": row[1],
                        "monto_total": float(row[2]) if row[2] else 0.0
                    })
                
                return {
                    "total_ventas": len(ventas),
                    "ventas": ventas,
                    "resumen_por_estado": resumen_estados
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/compare-ventas", tags=["Debug"])
async def compare_ventas_mongo_postgres():
    """
    Compara estados de ventas entre MongoDB y PostgreSQL.
    Útil para detectar desfases de sincronización.
    """
    import os
    from pymongo import MongoClient
    
    try:
        # Conectar a MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mongo_db_name]
        
        # Obtener ventas de MongoDB
        ventas_mongo = list(mongo_db.ventas.find({}, {
            '_id': 1,
            'estadoVenta': 1,
            'montoTotal': 1
        }))
        
        # Obtener ventas de PostgreSQL
        ventas_postgres = {}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT origen_id, estado, monto
                    FROM ventas
                """)
                for row in cur.fetchall():
                    ventas_postgres[row[0]] = {
                        'estado': row[1],
                        'monto': float(row[2]) if row[2] else 0.0
                    }
        
        mongo_client.close()
        
        # Comparar
        comparacion = []
        for venta_mongo in ventas_mongo:
            origen_id = str(venta_mongo['_id'])
            estado_mongo = (venta_mongo.get('estadoVenta') or '').lower()
            monto_mongo = venta_mongo.get('montoTotal', 0)
            
            if origen_id in ventas_postgres:
                estado_pg = ventas_postgres[origen_id]['estado']
                monto_pg = ventas_postgres[origen_id]['monto']
                
                sincronizado = (estado_mongo == estado_pg)
                
                comparacion.append({
                    'origen_id': origen_id,
                    'mongo': {
                        'estado': estado_mongo,
                        'monto': monto_mongo
                    },
                    'postgres': {
                        'estado': estado_pg,
                        'monto': monto_pg
                    },
                    'sincronizado': sincronizado,
                    'diferencia_estado': estado_mongo != estado_pg
                })
            else:
                comparacion.append({
                    'origen_id': origen_id,
                    'mongo': {
                        'estado': estado_mongo,
                        'monto': monto_mongo
                    },
                    'postgres': None,
                    'sincronizado': False,
                    'nota': 'No existe en PostgreSQL'
                })
        
        # Resumen
        total = len(comparacion)
        sincronizados = sum(1 for c in comparacion if c.get('sincronizado', False))
        
        return {
            'total_ventas': total,
            'sincronizadas': sincronizados,
            'desincronizadas': total - sincronizados,
            'comparacion': comparacion
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    - Total de ventas confirmadas (estado = 'confirmada')
    - Total de ventas pendientes (estado = 'pendiente')
    - Total de ventas canceladas (estado = 'cancelada')
    - Total de ventas (todas)
    - Total de monto vendido (solo confirmadas)
    - Total de monto pendiente (solo pendientes)
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
                
                # Total de ventas confirmadas (SOLO estado = 'confirmada')
                if ventas_where:
                    query = f"SELECT COUNT(*) FROM ventas v {ventas_where} AND v.estado = 'confirmada'"
                    cur.execute(query, params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'confirmada'")
                total_ventas_confirmadas = cur.fetchone()[0]
                
                # Total de ventas pendientes
                if ventas_where:
                    query = f"SELECT COUNT(*) FROM ventas v {ventas_where} AND v.estado = 'pendiente'"
                    cur.execute(query, params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'pendiente'")
                total_ventas_pendientes = cur.fetchone()[0]
                
                # Total de ventas canceladas
                if ventas_where:
                    query = f"SELECT COUNT(*) FROM ventas v {ventas_where} AND v.estado = 'cancelada'"
                    cur.execute(query, params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'cancelada'")
                total_ventas_canceladas = cur.fetchone()[0]
                
                # Total de monto vendido (SOLO ventas confirmadas)
                if ventas_where:
                    query = f"SELECT COALESCE(SUM(monto), 0) FROM ventas v {ventas_where} AND v.estado = 'confirmada'"
                    cur.execute(query, params)
                else:
                    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM ventas WHERE estado = 'confirmada'")
                total_monto_vendido = cur.fetchone()[0] or 0.0
                
                # Total de monto pendiente
                if ventas_where:
                    query = f"SELECT COALESCE(SUM(monto), 0) FROM ventas v {ventas_where} AND v.estado = 'pendiente'"
                    cur.execute(query, params)
                else:
                    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM ventas WHERE estado = 'pendiente'")
                total_monto_pendiente = cur.fetchone()[0] or 0.0
                
                # Total de ventas (todas)
                if ventas_where:
                    cur.execute(f"SELECT COUNT(*) FROM ventas v {ventas_where}", params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas")
                total_ventas = cur.fetchone()[0]
                
                # Tasa de cancelación
                if ventas_where:
                    query = f"SELECT COALESCE((COUNT(CASE WHEN v.estado = 'cancelada' THEN 1 END)::DECIMAL / NULLIF(COUNT(*), 0)) * 100, 0) FROM ventas v {ventas_where}"
                    cur.execute(query, params)
                else:
                    cur.execute("SELECT COALESCE((COUNT(CASE WHEN estado = 'cancelada' THEN 1 END)::DECIMAL / NULLIF(COUNT(*), 0)) * 100, 0) FROM ventas")
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
            total_ventas_pendientes=total_ventas_pendientes,
            total_ventas_canceladas=total_ventas_canceladas,
            total_ventas=total_ventas,
            total_monto_vendido=float(total_monto_vendido),
            total_monto_pendiente=float(total_monto_pendiente),
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
