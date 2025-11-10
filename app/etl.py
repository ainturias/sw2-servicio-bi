#!/usr/bin/env python3
"""
Script ETL para migrar datos de MongoDB a PostgreSQL.
Extrae datos de MongoDB y los sincroniza con PostgreSQL usando UPSERT por origen_id.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import pymongo
from pymongo import MongoClient
import psycopg
import time
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_mongo_client() -> MongoClient:
    """Conecta a MongoDB usando MONGO_URI"""
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI no está configurada")
    
    try:
        client = MongoClient(mongo_uri)
        # Verificar conexión
        client.admin.command('ping')
        logger.info("Conexión a MongoDB establecida")
        return client
    except Exception as e:
        logger.error(f"Error al conectar a MongoDB: {e}")
        raise


def get_pg_connection():
    """Conecta a PostgreSQL usando el Transaction Pooler de Supabase
    
    IMPORTANTE: ETL usa conexiones directas (no del pool) para evitar problemas
    con transacciones de larga duración y context managers.
    """
    # Siempre usar conexión directa para ETL
    # El pool se usa solo para endpoints HTTP de corta duración
    max_attempts = 3
    backoffs = [1, 2, 4]

    for attempt in range(1, max_attempts + 1):
        try:
            database = os.getenv("PG_DATABASE", os.getenv("dbname", "postgres"))
            user = os.getenv("PG_USER", os.getenv("user"))
            password = os.getenv("PG_PASSWORD", os.getenv("password"))
            host = os.getenv("PG_HOST", os.getenv("host", "aws-1-us-east-2.pooler.supabase.com"))
            port = os.getenv("PG_PORT", os.getenv("port", "6543"))
            sslmode = os.getenv("PG_SSLMODE", "require")
            conninfo = f"dbname={database} user={user} password={password} host={host} port={port} sslmode={sslmode}"
            conn = psycopg.connect(conninfo)
            logger.info("Conexión a PostgreSQL (directa) establecida para ETL")
            return conn
        except Exception as e:
            logger.warning(f"Intento {attempt}/{max_attempts} - error conectando a PostgreSQL: {e}")
            if attempt == max_attempts:
                logger.error(f"Error al conectar a PostgreSQL tras {max_attempts} intentos: {e}")
                raise
            sleep_for = backoffs[min(attempt - 1, len(backoffs) - 1)]
            logger.info(f"Reintentando en {sleep_for}s...")
            time.sleep(sleep_for)


def extract_collection(mongo_db, collection_name: str) -> List[Dict[str, Any]]:
    """Extrae una colección de MongoDB, retorna lista vacía si no existe"""
    try:
        collection = mongo_db[collection_name]
        data = list(collection.find({}))
        logger.info(f"Extraídos {len(data)} documentos de la colección '{collection_name}'")
        return data
    except Exception as e:
        logger.warning(f"Colección '{collection_name}' no existe o error al extraer: {e}")
        return []


def extract_clientes_with_usuarios(mongo_db) -> List[Dict[str, Any]]:
    """Extrae clientes haciendo lookup con usuarios para obtener nombre, email, etc.
    
    IMPORTANTE: El usuarioId en MongoDB puede estar como String en vez de ObjectId.
    Esta función convierte String a ObjectId antes del lookup.
    """
    from bson import ObjectId
    
    try:
        clientes_collection = mongo_db['clientes']
        
        # Agregación con conversión de String a ObjectId y lookup
        pipeline = [
            # Paso 1: Convertir usuarioId de String a ObjectId si es necesario
            {
                '$addFields': {
                    'usuarioIdConverted': {
                        '$cond': {
                            'if': {'$eq': [{'$type': '$usuarioId'}, 'string']},
                            'then': {'$toObjectId': '$usuarioId'},
                            'else': '$usuarioId'
                        }
                    }
                }
            },
            # Paso 2: Lookup usando el campo convertido
            {
                '$lookup': {
                    'from': 'usuarios',
                    'localField': 'usuarioIdConverted',
                    'foreignField': '_id',
                    'as': 'usuario'
                }
            },
            # Paso 3: Unwind para obtener el usuario como objeto (no array)
            {
                '$unwind': {
                    'path': '$usuario',
                    'preserveNullAndEmptyArrays': False  # Solo clientes con usuario válido
                }
            },
            # Paso 4: Limpiar el campo temporal
            {
                '$project': {
                    'usuarioIdConverted': 0
                }
            }
        ]
        
        data = list(clientes_collection.aggregate(pipeline))
        logger.info(f"✅ Extraídos {len(data)} clientes con lookup de usuarios (usuarioId convertido de String a ObjectId)")
        return data
    except Exception as e:
        logger.error(f"❌ Error al extraer clientes con usuarios: {e}")
        return []


def extract_agentes_with_usuarios(mongo_db) -> List[Dict[str, Any]]:
    """Extrae agentes haciendo lookup con usuarios para obtener nombre, email, etc.
    
    IMPORTANTE: El usuarioId en MongoDB puede estar como String en vez de ObjectId.
    Esta función convierte String a ObjectId antes del lookup.
    """
    from bson import ObjectId
    
    try:
        agentes_collection = mongo_db['agentes']
        
        # Agregación con conversión de String a ObjectId y lookup
        pipeline = [
            # Paso 1: Convertir usuarioId de String a ObjectId si es necesario
            {
                '$addFields': {
                    'usuarioIdConverted': {
                        '$cond': {
                            'if': {'$eq': [{'$type': '$usuarioId'}, 'string']},
                            'then': {'$toObjectId': '$usuarioId'},
                            'else': '$usuarioId'
                        }
                    }
                }
            },
            # Paso 2: Lookup usando el campo convertido
            {
                '$lookup': {
                    'from': 'usuarios',
                    'localField': 'usuarioIdConverted',
                    'foreignField': '_id',
                    'as': 'usuario'
                }
            },
            # Paso 3: Unwind para obtener el usuario como objeto (no array)
            {
                '$unwind': {
                    'path': '$usuario',
                    'preserveNullAndEmptyArrays': False  # Solo agentes con usuario válido
                }
            },
            # Paso 4: Limpiar el campo temporal
            {
                '$project': {
                    'usuarioIdConverted': 0
                }
            }
        ]
        
        data = list(agentes_collection.aggregate(pipeline))
        logger.info(f"✅ Extraídos {len(data)} agentes con lookup de usuarios (usuarioId convertido de String a ObjectId)")
        return data
    except Exception as e:
        logger.error(f"❌ Error al extraer agentes con usuarios: {e}")
        return []


def map_cliente(mongo_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mapea documento de cliente de MongoDB a PostgreSQL
    
    El documento viene con lookup de usuarios:
    {
        "_id": ObjectId,
        "usuarioId": ObjectId,
        "direccion": "...",
        "fechaNacimiento": ISODate,
        "numeroPasaporte": "...",
        "usuario": {
            "nombre": "...",
            "apellido": "...",
            "email": "...",
            "telefono": "..."
        }
    }
    """
    if not mongo_doc.get('_id'):
        return None
    
    # Obtener datos del usuario (viene del lookup)
    usuario = mongo_doc.get('usuario', {})
    
    # Construir nombre completo
    nombre = usuario.get('nombre', '')
    apellido = usuario.get('apellido', '')
    nombre_completo = f"{nombre} {apellido}".strip() if nombre or apellido else ''
    
    return {
        'origen_id': str(mongo_doc['_id']),
        'nombre': nombre_completo or 'Sin nombre',
        'email': usuario.get('email', ''),
        'telefono': usuario.get('telefono'),
        'fecha_registro': mongo_doc.get('fechaRegistro') or mongo_doc.get('fecha_registro') or datetime.now()
    }


def map_agente(mongo_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mapea documento de agente de MongoDB a PostgreSQL
    
    El documento viene con lookup de usuarios:
    {
        "_id": ObjectId,
        "usuarioId": ObjectId,
        "puesto": "...",
        "fechaContratacion": ISODate,
        "usuario": {
            "nombre": "...",
            "apellido": "...",
            "email": "...",
            "telefono": "..."
        }
    }
    """
    if not mongo_doc.get('_id'):
        return None
    
    # Obtener datos del usuario (viene del lookup)
    usuario = mongo_doc.get('usuario', {})
    
    # Construir nombre completo
    nombre = usuario.get('nombre', '')
    apellido = usuario.get('apellido', '')
    nombre_completo = f"{nombre} {apellido}".strip() if nombre or apellido else ''
    
    return {
        'origen_id': str(mongo_doc['_id']),
        'nombre': nombre_completo or 'Sin nombre',
        'email': usuario.get('email', ''),
        'telefono': usuario.get('telefono')
    }


def map_servicio(mongo_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mapea documento de servicio de MongoDB a PostgreSQL"""
    if not mongo_doc.get('_id'):
        return None
    
    # Extraer destino_ciudad y destino_pais por separado
    destino_ciudad = mongo_doc.get('destinoCiudad') or mongo_doc.get('destino_ciudad')
    destino_pais = mongo_doc.get('destinoPais') or mongo_doc.get('destino_pais')
    
    return {
        'origen_id': str(mongo_doc['_id']),
        'destino_ciudad': destino_ciudad,
        'destino_pais': destino_pais,
        'precio_costo': float(mongo_doc.get('precioCosto') or mongo_doc.get('precio_costo') or 0)
    }


def map_paquete_turistico(mongo_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mapea documento de paquete turístico de MongoDB a PostgreSQL"""
    if not mongo_doc.get('_id'):
        return None
    
    return {
        'origen_id': str(mongo_doc['_id']),
        'destino_principal': mongo_doc.get('destinoPrincipal') or mongo_doc.get('destino_principal'),
        'precio_total_venta': float(mongo_doc.get('precioTotalVenta') or mongo_doc.get('precio_total_venta') or 0)
    }


def map_venta(mongo_doc: Dict[str, Any], cliente_map: Dict[str, int], agente_map: Dict[str, int]) -> Optional[Dict[str, Any]]:
    """Mapea documento de venta de MongoDB a PostgreSQL"""
    if not mongo_doc.get('_id'):
        return None
    
    cliente_id = None
    if mongo_doc.get('clienteId') or mongo_doc.get('cliente_id'):
        cliente_origen_id = str(mongo_doc.get('clienteId') or mongo_doc.get('cliente_id'))
        cliente_id = cliente_map.get(cliente_origen_id)
    
    agente_id = None
    if mongo_doc.get('agenteId') or mongo_doc.get('agente_id'):
        agente_origen_id = str(mongo_doc.get('agenteId') or mongo_doc.get('agente_id'))
        agente_id = agente_map.get(agente_origen_id)
    
    # Mapear estado
    estado_mongo = mongo_doc.get('estadoVenta') or mongo_doc.get('estado_venta') or mongo_doc.get('estado', '')
    estado_pg = estado_mongo.lower() if estado_mongo else 'pendiente'
    
    # Mapear fecha_venta: convertir a date si es datetime
    fecha_venta_raw = mongo_doc.get('fechaVenta') or mongo_doc.get('fecha_venta') or datetime.now()
    if isinstance(fecha_venta_raw, datetime):
        fecha_venta = fecha_venta_raw.date()
    elif isinstance(fecha_venta_raw, str):
        # Intentar parsear string a date
        try:
            fecha_venta = datetime.fromisoformat(fecha_venta_raw.replace('Z', '+00:00')).date()
        except:
            fecha_venta = datetime.now().date()
    else:
        fecha_venta = datetime.now().date()
    
    return {
        'origen_id': str(mongo_doc['_id']),
        'cliente_id': cliente_id,
        'agente_id': agente_id,
        'estado': estado_pg,
        'monto': float(mongo_doc.get('montoTotal') or mongo_doc.get('monto_total') or mongo_doc.get('monto', 0)),
        'fecha_venta': fecha_venta,
        'puntuacion_satisfaccion': mongo_doc.get('puntuacionSatisfaccion') or mongo_doc.get('puntuacion_satisfaccion')
    }


def map_detalle_venta(mongo_doc: Dict[str, Any], venta_map: Dict[str, int], 
                      servicio_map: Dict[str, int], paquete_map: Dict[str, int]) -> Optional[Dict[str, Any]]:
    """Mapea documento de detalle_venta de MongoDB a PostgreSQL"""
    if not mongo_doc.get('_id'):
        return None
    
    venta_id = None
    if mongo_doc.get('ventaId') or mongo_doc.get('venta_id'):
        venta_origen_id = str(mongo_doc.get('ventaId') or mongo_doc.get('venta_id'))
        venta_id = venta_map.get(venta_origen_id)
    
    servicio_id = None
    if mongo_doc.get('servicioId') or mongo_doc.get('servicio_id'):
        servicio_origen_id = str(mongo_doc.get('servicioId') or mongo_doc.get('servicio_id'))
        servicio_id = servicio_map.get(servicio_origen_id)
    
    paquete_id = None
    if mongo_doc.get('paqueteId') or mongo_doc.get('paquete_id'):
        paquete_origen_id = str(mongo_doc.get('paqueteId') or mongo_doc.get('paquete_id'))
        paquete_id = paquete_map.get(paquete_origen_id)
    
    return {
        'origen_id': str(mongo_doc['_id']),
        'venta_id': venta_id,
        'servicio_id': servicio_id,
        'paquete_id': paquete_id,
        'descripcion': mongo_doc.get('descripcion', ''),
        'cantidad': int(mongo_doc.get('cantidad', 1)),
        'precio_unitario': float(mongo_doc.get('precioUnitario') or mongo_doc.get('precio_unitario') or 0),
        'subtotal': float(mongo_doc.get('subtotal', 0))
    }


def upsert_clientes(conn, clientes: List[Dict[str, Any]]) -> tuple[int, int]:
    """Hace UPSERT de clientes en PostgreSQL"""
    if not clientes:
        return 0, 0
    
    insertados = 0
    actualizados = 0
    
    for cliente in clientes:
        # Usar un cursor nuevo para cada operación para evitar problemas de prepared statements
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO clientes (origen_id, nombre, email, telefono, fecha_registro)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (origen_id) 
                DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    email = EXCLUDED.email,
                    telefono = EXCLUDED.telefono,
                    fecha_registro = EXCLUDED.fecha_registro
            """, (
                cliente['origen_id'],
                cliente['nombre'],
                cliente['email'],
                cliente['telefono'],
                cliente['fecha_registro']
            ))
            
            if cur.rowcount == 1:
                insertados += 1
            else:
                actualizados += 1
        except Exception as e:
            logger.error(f"Error al procesar cliente {cliente.get('origen_id')}: {e}")
            # Hacer rollback y reiniciar transacción para poder continuar
            conn.rollback()
        finally:
            cur.close()
    
    return insertados, actualizados


def upsert_agentes(conn, agentes: List[Dict[str, Any]]) -> tuple[int, int]:
    """Hace UPSERT de agentes en PostgreSQL"""
    if not agentes:
        return 0, 0
    
    # Primero crear la tabla si no existe
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agentes (
                id SERIAL PRIMARY KEY,
                origen_id VARCHAR(255) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                telefono VARCHAR(20)
            )
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Error al crear tabla agentes: {e}")
        conn.rollback()
    
    insertados = 0
    actualizados = 0
    
    for agente in agentes:
        try:
            cur.execute("""
                INSERT INTO agentes (origen_id, nombre, email, telefono)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (origen_id) 
                DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    email = EXCLUDED.email,
                    telefono = EXCLUDED.telefono
            """, (
                agente['origen_id'],
                agente['nombre'],
                agente['email'],
                agente['telefono']
            ))
            
            if cur.rowcount == 1:
                insertados += 1
            else:
                actualizados += 1
        except Exception as e:
            logger.error(f"Error al procesar agente {agente.get('origen_id')}: {e}")
            continue
    
    return insertados, actualizados


def upsert_servicios(conn, servicios: List[Dict[str, Any]]) -> tuple[int, int]:
    """Hace UPSERT de servicios en PostgreSQL"""
    if not servicios:
        return 0, 0
    
    # Crear tabla si no existe (con destino_pais)
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS servicios (
                id SERIAL PRIMARY KEY,
                origen_id VARCHAR(255) UNIQUE NOT NULL,
                destino_ciudad VARCHAR(200),
                destino_pais VARCHAR(100),
                precio_costo DECIMAL(10, 2) DEFAULT 0
            )
        """)
        # Agregar columna destino_pais si no existe
        cur.execute("""
            ALTER TABLE servicios 
            ADD COLUMN IF NOT EXISTS destino_pais VARCHAR(100)
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Error al crear/modificar tabla servicios: {e}")
        conn.rollback()
    
    insertados = 0
    actualizados = 0
    
    for servicio in servicios:
        try:
            cur.execute("""
                INSERT INTO servicios (origen_id, destino_ciudad, destino_pais, precio_costo)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (origen_id) 
                DO UPDATE SET
                    destino_ciudad = EXCLUDED.destino_ciudad,
                    destino_pais = EXCLUDED.destino_pais,
                    precio_costo = EXCLUDED.precio_costo
            """, (
                servicio['origen_id'],
                servicio['destino_ciudad'],
                servicio['destino_pais'],
                servicio['precio_costo']
            ))
            
            if cur.rowcount == 1:
                insertados += 1
            else:
                actualizados += 1
        except Exception as e:
            logger.error(f"Error al procesar servicio {servicio.get('origen_id')}: {e}")
            continue
    
    return insertados, actualizados


def upsert_paquetes_turisticos(conn, paquetes: List[Dict[str, Any]]) -> tuple[int, int]:
    """Hace UPSERT de paquetes turísticos en PostgreSQL"""
    if not paquetes:
        return 0, 0
    
    # Crear tabla si no existe
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paquetes_turisticos (
                id SERIAL PRIMARY KEY,
                origen_id VARCHAR(255) UNIQUE NOT NULL,
                destino_principal VARCHAR(200),
                precio_total_venta DECIMAL(10, 2)
            )
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Error al crear tabla paquetes_turisticos: {e}")
        conn.rollback()
    
    insertados = 0
    actualizados = 0
    
    for paquete in paquetes:
        try:
            cur.execute("""
                INSERT INTO paquetes_turisticos (origen_id, destino_principal, precio_total_venta)
                VALUES (%s, %s, %s)
                ON CONFLICT (origen_id) 
                DO UPDATE SET
                    destino_principal = EXCLUDED.destino_principal,
                    precio_total_venta = EXCLUDED.precio_total_venta
            """, (
                paquete['origen_id'],
                paquete['destino_principal'],
                paquete['precio_total_venta']
            ))
            
            if cur.rowcount == 1:
                insertados += 1
            else:
                actualizados += 1
        except Exception as e:
            logger.error(f"Error al procesar paquete {paquete.get('origen_id')}: {e}")
            continue
    
    return insertados, actualizados


def upsert_ventas(conn, ventas: List[Dict[str, Any]]) -> tuple[int, int, Dict[str, int]]:
    """Hace UPSERT de ventas en PostgreSQL y retorna mapa origen_id -> id"""
    if not ventas:
        return 0, 0, {}
    
    # Asegurar que la tabla tiene origen_id
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE ventas 
            ADD COLUMN IF NOT EXISTS origen_id VARCHAR(255) UNIQUE
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Error al agregar columna origen_id a ventas: {e}")
        conn.rollback()
    
    insertados = 0
    actualizados = 0
    venta_map = {}
    
    for venta in ventas:
        try:
            cur.execute("""
                INSERT INTO ventas (origen_id, cliente_id, agente_id, estado, monto, fecha_venta, puntuacion_satisfaccion)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (origen_id) 
                DO UPDATE SET
                    cliente_id = EXCLUDED.cliente_id,
                    agente_id = EXCLUDED.agente_id,
                    estado = EXCLUDED.estado,
                    monto = EXCLUDED.monto,
                    fecha_venta = EXCLUDED.fecha_venta,
                    puntuacion_satisfaccion = EXCLUDED.puntuacion_satisfaccion
                RETURNING id
            """, (
                venta['origen_id'],
                venta['cliente_id'],
                venta['agente_id'],
                venta['estado'],
                venta['monto'],
                venta['fecha_venta'],
                venta.get('puntuacion_satisfaccion')
            ))
            
            result = cur.fetchone()
            if result:
                venta_map[venta['origen_id']] = result[0]
            
            if cur.rowcount == 1:
                insertados += 1
            else:
                actualizados += 1
        except Exception as e:
            logger.error(f"Error al procesar venta {venta.get('origen_id')}: {e}")
            continue
    
    return insertados, actualizados, venta_map


def upsert_detalle_venta(conn, detalles: List[Dict[str, Any]]) -> tuple[int, int]:
    """Hace UPSERT de detalles de venta en PostgreSQL"""
    if not detalles:
        return 0, 0
    
    # Asegurar que la tabla tiene origen_id
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE detalle_venta 
            ADD COLUMN IF NOT EXISTS origen_id VARCHAR(255) UNIQUE,
            ADD COLUMN IF NOT EXISTS servicio_id INTEGER REFERENCES servicios(id),
            ADD COLUMN IF NOT EXISTS paquete_id INTEGER REFERENCES paquetes_turisticos(id)
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Error al modificar tabla detalle_venta: {e}")
        conn.rollback()
    
    insertados = 0
    actualizados = 0
    
    for detalle in detalles:
        try:
            cur.execute("""
                INSERT INTO detalle_venta (origen_id, venta_id, servicio_id, paquete_id, descripcion, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (origen_id) 
                DO UPDATE SET
                    venta_id = EXCLUDED.venta_id,
                    servicio_id = EXCLUDED.servicio_id,
                    paquete_id = EXCLUDED.paquete_id,
                    descripcion = EXCLUDED.descripcion,
                    cantidad = EXCLUDED.cantidad,
                    precio_unitario = EXCLUDED.precio_unitario,
                    subtotal = EXCLUDED.subtotal
            """, (
                detalle['origen_id'],
                detalle['venta_id'],
                detalle['servicio_id'],
                detalle['paquete_id'],
                detalle['descripcion'],
                detalle['cantidad'],
                detalle['precio_unitario'],
                detalle['subtotal']
            ))
            
            if cur.rowcount == 1:
                insertados += 1
            else:
                actualizados += 1
        except Exception as e:
            logger.error(f"Error al procesar detalle_venta {detalle.get('origen_id')}: {e}")
            continue
    
    return insertados, actualizados


def get_id_map(conn, table_name: str) -> Dict[str, int]:
    """Obtiene mapa de origen_id -> id de una tabla"""
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT origen_id, id FROM {table_name}")
        return {row[0]: row[1] for row in cur.fetchall() if row[0]}
    except Exception as e:
        logger.warning(f"Error al obtener mapa de {table_name}: {e}")
        return {}


def sync_data():
    """
    Función para sincronizar datos (versión simplificada de main)
    Usada por la sincronización en tiempo real
    """
    # Hacemos varios intentos completos de sincronización (ETL) para cubrir
    # fallos transitorios como pools cerrados o conexiones temporales.
    max_attempts = 3
    backoffs = [1, 2, 4]

    for attempt in range(1, max_attempts + 1):
        # Evitar iniciar la sincronización si el worker está en proceso de parada
        try:
            from app.realtime_sync import realtime_sync
            if getattr(realtime_sync, '_stop_event', None) is not None and realtime_sync._stop_event.is_set():
                logger.info("sync_data: stop event set, abortando sincronización")
                return
        except Exception:
            # Si no se puede importar el realtime_sync por alguna razón, continuar
            pass

        mongo_client = None
        pg_conn = None
        try:
            logger.info(f"sync_data: intento {attempt}/{max_attempts}")
            # Conectar a MongoDB
            mongo_client = get_mongo_client()
            mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
            mongo_db = mongo_client[mongo_db_name]

            # Conectar a PostgreSQL (get_pg_connection tiene reintentos)
            try:
                pg_conn = get_pg_connection()
            except Exception as e:
                logger.error(f"sync_data: no se pudo obtener conexión a PostgreSQL: {e}")
                raise

            pg_conn.autocommit = False

            # Extraer datos de MongoDB
            clientes_mongo = extract_clientes_with_usuarios(mongo_db)  # Lookup con usuarios
            agentes_mongo = extract_agentes_with_usuarios(mongo_db)  # Lookup con usuarios
            servicios_mongo = extract_collection(mongo_db, "servicios")
            paquetes_mongo = extract_collection(mongo_db, "paquetesTuristicos")
            ventas_mongo = extract_collection(mongo_db, "ventas")
            detalles_mongo = extract_collection(mongo_db, "detalleVenta")

            # Transformar y cargar datos
            clientes_pg = [map_cliente(doc) for doc in clientes_mongo]
            clientes_pg = [c for c in clientes_pg if c is not None]
            upsert_clientes(pg_conn, clientes_pg)
            pg_conn.commit()

            agentes_pg = [map_agente(doc) for doc in agentes_mongo]
            agentes_pg = [a for a in agentes_pg if a is not None]
            upsert_agentes(pg_conn, agentes_pg)
            pg_conn.commit()

            servicios_pg = [map_servicio(doc) for doc in servicios_mongo]
            servicios_pg = [s for s in servicios_pg if s is not None]
            upsert_servicios(pg_conn, servicios_pg)
            pg_conn.commit()

            paquetes_pg = [map_paquete_turistico(doc) for doc in paquetes_mongo]
            paquetes_pg = [p for p in paquetes_pg if p is not None]
            upsert_paquetes_turisticos(pg_conn, paquetes_pg)
            pg_conn.commit()

            cliente_map = get_id_map(pg_conn, "clientes")
            agente_map = get_id_map(pg_conn, "agentes")
            servicio_map = get_id_map(pg_conn, "servicios")
            paquete_map = get_id_map(pg_conn, "paquetes_turisticos")

            ventas_pg = [map_venta(doc, cliente_map, agente_map) for doc in ventas_mongo]
            ventas_pg = [v for v in ventas_pg if v is not None]
            insertados, actualizados, venta_map = upsert_ventas(pg_conn, ventas_pg)
            pg_conn.commit()

            detalles_pg = [map_detalle_venta(doc, venta_map, servicio_map, paquete_map) for doc in detalles_mongo]
            detalles_pg = [d for d in detalles_pg if d is not None]
            upsert_detalle_venta(pg_conn, detalles_pg)
            pg_conn.commit()

            # Si llegamos aquí, la sincronización fue exitosa
            logger.info("sync_data: sincronización completada con éxito")
            # Cerrar conexiones y salir
            try:
                if pg_conn:
                    pg_conn.close()
            except Exception:
                pass
            try:
                if mongo_client:
                    mongo_client.close()
            except Exception:
                pass
            return

        except Exception as e:
            # Si el stop event está seteado, abortar inmediatamente
            try:
                from app.realtime_sync import realtime_sync
                if getattr(realtime_sync, '_stop_event', None) is not None and realtime_sync._stop_event.is_set():
                    logger.info("sync_data: stop event set durante intento - abortando")
                    try:
                        if pg_conn:
                            pg_conn.close()
                    except Exception:
                        pass
                    try:
                        if mongo_client:
                            mongo_client.close()
                    except Exception:
                        pass
                    return
            except Exception:
                pass

            msg = str(e).lower()
            logger.warning(f"sync_data: intento {attempt} falló: {e}")
            # Si fue el último intento, registrar y salir
            if attempt == max_attempts:
                logger.error(f"sync_data: falló después de {max_attempts} intentos: {e}")
                try:
                    if pg_conn:
                        pg_conn.close()
                except Exception:
                    pass
                try:
                    if mongo_client:
                        mongo_client.close()
                except Exception:
                    pass
                return

            # Sleep con backoff antes de reintentar
            sleep_for = backoffs[min(attempt - 1, len(backoffs) - 1)]
            logger.info(f"sync_data: reintentando en {sleep_for}s...")
            try:
                if pg_conn:
                    pg_conn.close()
            except Exception:
                pass
            try:
                if mongo_client:
                    mongo_client.close()
            except Exception:
                pass
            time.sleep(sleep_for)


def main():
    """Función principal del ETL"""
    logger.info("=" * 60)
    logger.info("Iniciando proceso ETL")
    logger.info("=" * 60)
    
    try:
        # Conectar a MongoDB
        mongo_client = get_mongo_client()
        # Obtener nombre de base de datos desde variable de entorno o usar default
        mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
        mongo_db = mongo_client[mongo_db_name]
        
        # Conectar a PostgreSQL
        pg_conn = get_pg_connection()
        pg_conn.autocommit = False  # Usar transacciones
        
        try:
            # Extraer datos de MongoDB
            logger.info("\n--- EXTRACCIÓN DE DATOS ---")
            clientes_mongo = extract_clientes_with_usuarios(mongo_db)  # Lookup con usuarios
            agentes_mongo = extract_agentes_with_usuarios(mongo_db)  # Lookup con usuarios
            servicios_mongo = extract_collection(mongo_db, "servicios")
            paquetes_mongo = extract_collection(mongo_db, "paquetesTuristicos")
            ventas_mongo = extract_collection(mongo_db, "ventas")
            detalles_mongo = extract_collection(mongo_db, "detalleVenta")
            
            # Transformar y cargar datos
            logger.info("\n--- TRANSFORMACIÓN Y CARGA ---")
            
            # 1. Clientes
            logger.info("\nProcesando clientes...")
            clientes_pg = [map_cliente(doc) for doc in clientes_mongo]
            clientes_pg = [c for c in clientes_pg if c is not None]
            insertados, actualizados = upsert_clientes(pg_conn, clientes_pg)
            logger.info(f"Clientes: {insertados} insertados, {actualizados} actualizados")
            pg_conn.commit()
            
            # 2. Agentes
            logger.info("\nProcesando agentes...")
            agentes_pg = [map_agente(doc) for doc in agentes_mongo]
            agentes_pg = [a for a in agentes_pg if a is not None]
            insertados, actualizados = upsert_agentes(pg_conn, agentes_pg)
            logger.info(f"Agentes: {insertados} insertados, {actualizados} actualizados")
            pg_conn.commit()
            
            # 3. Servicios
            logger.info("\nProcesando servicios...")
            servicios_pg = [map_servicio(doc) for doc in servicios_mongo]
            servicios_pg = [s for s in servicios_pg if s is not None]
            insertados, actualizados = upsert_servicios(pg_conn, servicios_pg)
            logger.info(f"Servicios: {insertados} insertados, {actualizados} actualizados")
            pg_conn.commit()
            
            # 4. Paquetes turísticos
            logger.info("\nProcesando paquetes turísticos...")
            paquetes_pg = [map_paquete_turistico(doc) for doc in paquetes_mongo]
            paquetes_pg = [p for p in paquetes_pg if p is not None]
            insertados, actualizados = upsert_paquetes_turisticos(pg_conn, paquetes_pg)
            logger.info(f"Paquetes turísticos: {insertados} insertados, {actualizados} actualizados")
            pg_conn.commit()
            
            # Obtener mapas de IDs para relaciones
            cliente_map = get_id_map(pg_conn, "clientes")
            agente_map = get_id_map(pg_conn, "agentes")
            servicio_map = get_id_map(pg_conn, "servicios")
            paquete_map = get_id_map(pg_conn, "paquetes_turisticos")
            
            # 5. Ventas
            logger.info("\nProcesando ventas...")
            ventas_pg = [map_venta(doc, cliente_map, agente_map) for doc in ventas_mongo]
            ventas_pg = [v for v in ventas_pg if v is not None]
            insertados, actualizados, venta_map = upsert_ventas(pg_conn, ventas_pg)
            logger.info(f"Ventas: {insertados} insertados, {actualizados} actualizados")
            pg_conn.commit()
            
            # 6. Detalles de venta
            logger.info("\nProcesando detalles de venta...")
            detalles_pg = [map_detalle_venta(doc, venta_map, servicio_map, paquete_map) for doc in detalles_mongo]
            detalles_pg = [d for d in detalles_pg if d is not None]
            insertados, actualizados = upsert_detalle_venta(pg_conn, detalles_pg)
            logger.info(f"Detalles de venta: {insertados} insertados, {actualizados} actualizados")
            pg_conn.commit()
            
            logger.info("\n" + "=" * 60)
            logger.info("Proceso ETL completado exitosamente")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error durante el proceso ETL: {e}")
            pg_conn.rollback()
            raise
        finally:
            pg_conn.close()
            mongo_client.close()
            
    except Exception as e:
        logger.error(f"Error fatal en ETL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

