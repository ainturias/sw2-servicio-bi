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
import os
from app.db import get_conn, init_pool, close_pool
from app.realtime_sync import start_realtime_sync, stop_realtime_sync
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Business Intelligence Service",
    description="Microservicio de BI para agencia de viajes - Solo endpoints esenciales",
    version="3.0.0"
)


# =============================================================================
# EVENTOS DE INICIO/CIERRE
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Iniciar la sincronización en tiempo real al arrancar la aplicación"""
    logger.info("🚀 Iniciando aplicación...")
    try:
        init_pool(min_size=1, max_size=5)
        logger.info("✅ Pool de PostgreSQL inicializado")
        
        # Sincronización inicial completa al arrancar
        logger.info("🔄 Ejecutando sincronización inicial de datos...")
        from app.etl import sync_data
        try:
            sync_data()
            logger.info("✅ Sincronización inicial completada")
        except Exception as sync_error:
            logger.error(f"⚠️ Error en sincronización inicial: {sync_error}")
        
        # Activar Change Streams para cambios en tiempo real
        if start_realtime_sync():
            logger.info("✅ Sincronización en tiempo real activada")
        else:
            logger.warning("⚠️ No se pudo activar la sincronización en tiempo real")
    except Exception as e:
        logger.error(f"❌ Error al iniciar: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Detener la sincronización al cerrar la aplicación"""
    logger.info("⏹️ Deteniendo aplicación...")
    stop_realtime_sync()
    try:
        close_pool()
        logger.info("✅ Pool de PostgreSQL cerrado")
    except Exception as e:
        logger.warning(f"Error cerrando pool: {e}")
    logger.info("👋 Aplicación detenida")


# =============================================================================
# MODELOS PYDANTIC
# =============================================================================

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


# =============================================================================
# ENDPOINTS DE HEALTH
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Endpoint de salud del servicio.
    """
    return HealthResponse(status="ok")


@app.get("/sync/status", tags=["Sync"])
async def sync_status():
    """
    Verificar el estado de la sincronización en tiempo real.
    """
    from app.realtime_sync import realtime_sync
    return {
        "sync_enabled": True,
        "sync_running": realtime_sync.is_running,
        "message": "Sincronización en tiempo real activa" if realtime_sync.is_running else "Sincronización no activa"
    }


@app.post("/sync/force", tags=["Sync"])
async def force_sync():
    """
    Forzar sincronización inmediata de MongoDB a PostgreSQL.
    Llamar después de cambiar datos en MongoDB.
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


@app.post("/sync/fix-ventas", tags=["Sync"])
async def fix_ventas_estados():
    """
    Fix para actualizar estados de ventas cuando el UPDATE no funciona.
    Actualiza directamente desde MongoDB a PostgreSQL.
    """
    from pymongo import MongoClient
    
    try:
        logger.info("🔧 Forzando actualización directa de estados...")
        
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[mongo_db_name]
        
        ventas_mongo = list(mongo_db.ventas.find({}, {
            '_id': 1,
            'estadoVenta': 1,
            'montoTotal': 1
        }))
        
        actualizados = 0
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                for venta in ventas_mongo:
                    origen_id = str(venta['_id'])
                    estado = (venta.get('estadoVenta') or '').lower()
                    monto = venta.get('montoTotal', 0)
                    
                    cur.execute("""
                        UPDATE ventas 
                        SET estado = %s, monto = %s
                        WHERE origen_id = %s
                    """, (estado, monto, origen_id))
                    
                    if cur.rowcount > 0:
                        actualizados += 1
                
                conn.commit()
        
        mongo_client.close()
        
        logger.info(f"✅ Fix completado: {actualizados} ventas actualizadas")
        return {
            "status": "success",
            "message": f"Fix completado: {actualizados} ventas actualizadas",
            "actualizados": actualizados
        }
        
    except Exception as e:
        logger.error(f"❌ Error en fix de ventas: {e}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


# =============================================================================
# DASHBOARD PRINCIPAL
# =============================================================================

@app.get("/dashboard/resumen", response_model=DashboardResumenResponse, tags=["Dashboard"])
async def obtener_resumen_dashboard(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> DashboardResumenResponse:
    """
    Dashboard principal con todos los KPIs y métricas.
    
    Retorna:
    - Total de clientes
    - Ventas (confirmadas, pendientes, canceladas, total)
    - Montos (vendido, pendiente)
    - Tasa de cancelación
    - Top 5 destinos por ingresos
    - Tendencia de reservas por día
    
    Parámetros opcionales:
    - fecha_inicio: Filtrar desde esta fecha (YYYY-MM-DD)
    - fecha_fin: Filtrar hasta esta fecha (YYYY-MM-DD)
    """
    try:
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
        
        ventas_where = where_clause.replace("fecha_venta", "v.fecha_venta") if where_clause else ""
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Total de clientes
                cur.execute("SELECT COUNT(*) FROM clientes")
                total_clientes = cur.fetchone()[0]
                
                # Ventas confirmadas
                if ventas_where:
                    cur.execute(f"SELECT COUNT(*) FROM ventas v {ventas_where} AND v.estado = 'confirmada'", params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'confirmada'")
                total_ventas_confirmadas = cur.fetchone()[0]
                
                # Ventas pendientes
                if ventas_where:
                    cur.execute(f"SELECT COUNT(*) FROM ventas v {ventas_where} AND v.estado = 'pendiente'", params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'pendiente'")
                total_ventas_pendientes = cur.fetchone()[0]
                
                # Ventas canceladas
                if ventas_where:
                    cur.execute(f"SELECT COUNT(*) FROM ventas v {ventas_where} AND v.estado = 'cancelada'", params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas WHERE estado = 'cancelada'")
                total_ventas_canceladas = cur.fetchone()[0]
                
                # Monto vendido (confirmadas)
                if ventas_where:
                    cur.execute(f"SELECT COALESCE(SUM(monto), 0) FROM ventas v {ventas_where} AND v.estado = 'confirmada'", params)
                else:
                    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM ventas WHERE estado = 'confirmada'")
                total_monto_vendido = cur.fetchone()[0] or 0.0
                
                # Monto pendiente
                if ventas_where:
                    cur.execute(f"SELECT COALESCE(SUM(monto), 0) FROM ventas v {ventas_where} AND v.estado = 'pendiente'", params)
                else:
                    cur.execute("SELECT COALESCE(SUM(monto), 0) FROM ventas WHERE estado = 'pendiente'")
                total_monto_pendiente = cur.fetchone()[0] or 0.0
                
                # Total de ventas
                if ventas_where:
                    cur.execute(f"SELECT COUNT(*) FROM ventas v {ventas_where}", params)
                else:
                    cur.execute("SELECT COUNT(*) FROM ventas")
                total_ventas = cur.fetchone()[0]
                
                # Tasa de cancelación
                if ventas_where:
                    cur.execute(f"SELECT COALESCE((COUNT(CASE WHEN v.estado = 'cancelada' THEN 1 END)::DECIMAL / NULLIF(COUNT(*), 0)) * 100, 0) FROM ventas v {ventas_where}", params)
                else:
                    cur.execute("SELECT COALESCE((COUNT(CASE WHEN estado = 'cancelada' THEN 1 END)::DECIMAL / NULLIF(COUNT(*), 0)) * 100, 0) FROM ventas")
                tasa_cancelacion = float(cur.fetchone()[0] or 0.0)
                
                # Top 5 destinos
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
                
                cur.execute(f"""
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
                """, params_top)
                
                top_destinos = [
                    TopDestino(destino=row[0] or "Sin destino", ingresos=round(float(row[1] or 0.0), 2))
                    for row in cur.fetchall()
                ]
                
                # Tendencia de reservas por día
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
                
                cur.execute(f"""
                    SELECT 
                        DATE(fecha_venta) as fecha,
                        COUNT(*) as cantidad_reservas
                    FROM ventas v
                    WHERE v.estado = 'confirmada'
                    {fecha_where_tendencia}
                    GROUP BY DATE(fecha_venta)
                    ORDER BY fecha ASC
                """, params_tendencia)
                
                tendencia_reservas_por_dia = [
                    TendenciaDia(
                        fecha=row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                        cantidad_reservas=int(row[1] or 0)
                    )
                    for row in cur.fetchall()
                ]
        
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


# =============================================================================
# KPIs INDIVIDUALES
# =============================================================================

@app.get("/kpi/margen-bruto", response_model=MargenBrutoResponse, tags=["KPI"])
async def obtener_margen_bruto(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
) -> MargenBrutoResponse:
    """
    Calcula el margen bruto de ganancia por reserva.
    
    Fórmula: ((ingresos - costos) / ingresos) × 100
    
    - Ingresos: SUM(detalle_venta.subtotal)
    - Costos: precio_costo de servicios o 75% del precio de paquetes
    """
    try:
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
                cur.execute(f"""
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
                """, params)
                
                result = cur.fetchone()
                ingresos = float(result[0] or 0.0)
                costo = float(result[1] or 0.0)
                margen_bruto_pct = float(result[2] or 0.0)
        
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
    Calcula la tasa de conversión de reservas.
    
    Fórmula: (ventas confirmadas / total de ventas) × 100
    """
    try:
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
                cur.execute(f"""
                    SELECT COALESCE(
                        (COUNT(CASE WHEN estado = 'confirmada' THEN 1 END)::DECIMAL / 
                         NULLIF(COUNT(*), 0)) * 100,
                        0
                    ) as tasa_conversion
                    FROM ventas
                    {fecha_where}
                """, params)
                
                tasa_conversion = float(cur.fetchone()[0] or 0.0)
        
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
    Calcula la tasa de cancelación de ventas.
    
    Fórmula: (ventas canceladas / total de ventas) × 100
    """
    try:
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
                cur.execute(f"""
                    SELECT COALESCE(
                        (COUNT(CASE WHEN estado = 'cancelada' THEN 1 END)::DECIMAL / 
                         NULLIF(COUNT(*), 0)) * 100,
                        0
                    ) as tasa_cancelacion
                    FROM ventas
                    {fecha_where}
                """, params)
                
                tasa_cancelacion = float(cur.fetchone()[0] or 0.0)
        
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


# =============================================================================
# EXPORT
# =============================================================================

@app.get("/export/ventas.csv", tags=["Export"])
async def exportar_ventas_csv(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None
):
    """
    Exporta ventas confirmadas a formato CSV.
    
    Columnas:
    - venta_id, fecha_venta, cliente_id, agente_id
    - estado_venta, monto_total, destino
    - cantidad, precio_unitario_venta, subtotal
    """
    try:
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
            with get_conn() as conn:
                output = io.StringIO()
                writer = csv.writer(output)
                
                writer.writerow([
                    'venta_id', 'fecha_venta', 'cliente_id', 'agente_id',
                    'estado_venta', 'monto_total', 'destino',
                    'cantidad', 'precio_unitario_venta', 'subtotal'
                ])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
                
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    
                    for row in cur:
                        writer.writerow([
                            row[0] or '',
                            row[1].isoformat() if row[1] else '',
                            row[2] or '',
                            row[3] or '',
                            row[4] or '',
                            float(row[5]) if row[5] is not None else 0.0,
                            row[6] or 'Sin destino',
                            row[7] or 0,
                            float(row[8]) if row[8] is not None else 0.0,
                            float(row[9]) if row[9] is not None else 0.0
                        ])
                        yield output.getvalue()
                        output.seek(0)
                        output.truncate(0)
        
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="ventas.csv"'}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar ventas a CSV: {str(e)}"
        )
