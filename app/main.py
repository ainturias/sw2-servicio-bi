from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import csv
import io
from app.db import get_conn
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
        
        conn = get_conn()
        
        with conn:
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
        
        conn = get_conn()
        
        with conn:
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
        
        conn = get_conn()
        
        with conn:
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
        
        conn = get_conn()
        
        with conn:
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
        
        conn = get_conn()
        
        with conn:
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
        
        conn = get_conn()
        
        with conn:
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
            conn = get_conn()
            try:
                with conn:
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
            finally:
                conn.close()
        
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