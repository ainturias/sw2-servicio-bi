import os
import psycopg
from psycopg import Connection
from dotenv import load_dotenv
from typing import Optional

# psycopg pool (psycopg 3)
try:
    from psycopg_pool import ConnectionPool
except Exception:
    ConnectionPool = None  # type: ignore

# Cargar variables de entorno desde .env si existe
load_dotenv()


# Pool global (inicializado en startup)
_POOL: Optional["ConnectionPool"] = None
_CONNINFO: Optional[str] = None


def init_pool(min_size: int = 1, max_size: int = 5):
    """Inicializa un pool de conexiones global que será usado por la app.

    Llamar desde el evento de startup de FastAPI.
    """
    global _POOL, _CONNINFO
    if _POOL is not None:
        return _POOL

    database = os.getenv("PG_DATABASE", os.getenv("dbname", "postgres"))
    user = os.getenv("PG_USER", os.getenv("user"))
    password = os.getenv("PG_PASSWORD", os.getenv("password"))
    host = os.getenv("PG_HOST", os.getenv("host", "aws-1-us-east-2.pooler.supabase.com"))
    port = os.getenv("PG_PORT", os.getenv("port", "6543"))
    sslmode = os.getenv("PG_SSLMODE", "require")

    if not all([database, user, password]):
        raise ValueError("PG_DATABASE/PG_USER/PG_PASSWORD deben estar configuradas para inicializar el pool")

    _CONNINFO = f"dbname={database} user={user} password={password} host={host} port={port} sslmode={sslmode}"

    if ConnectionPool is None:
        # Fallback: no pool disponible en el entorno (ej: dependencia no instalada)
        raise RuntimeError("psycopg_pool no disponible. Asegúrate de instalar psycopg[binary]")

    _POOL = ConnectionPool(conninfo=_CONNINFO, min_size=min_size, max_size=max_size)
    return _POOL


def close_pool():
    """Cierra el pool global si existe. Llamar desde shutdown."""
    global _POOL
    if _POOL is not None:
        try:
            _POOL.close()
        finally:
            _POOL = None


def get_conn() -> Connection:
    """
    Crea y retorna una conexión a PostgreSQL usando el Transaction Pooler de Supabase.
    
    Variables de entorno requeridas:
    - user: Usuario de PostgreSQL (formato: postgres.<proyecto_id>)
    - password: Contraseña de PostgreSQL
    - host: Host del pooler (aws-1-us-east-2.pooler.supabase.com)
    - port: Puerto del pooler (default: 6543)
    - dbname: Nombre de la base de datos (default: postgres)
    
    Returns:
        Connection: Conexión a la base de datos PostgreSQL
        
    Raises:
        ValueError: Si faltan variables de entorno requeridas
        psycopg.Error: Si hay un error al conectar con la base de datos
    """
    # Leer variables de entorno con prefijo PG_
    database = os.getenv("PG_DATABASE", os.getenv("dbname", "postgres"))
    user = os.getenv("PG_USER", os.getenv("user"))
    password = os.getenv("PG_PASSWORD", os.getenv("password"))
    host = os.getenv("PG_HOST", os.getenv("host", "aws-1-us-east-2.pooler.supabase.com"))
    port = os.getenv("PG_PORT", os.getenv("port", "6543"))
    sslmode = os.getenv("PG_SSLMODE", "require")  # require para Supabase, disable para local

    # Validar variables requeridas
    if not database:
        raise ValueError("PG_DATABASE no está configurada")
    if not user:
        raise ValueError("PG_USER no está configurada")
    if not password:
        raise ValueError("PG_PASSWORD no está configurada")

    # Construir connection string para psycopg 3.x si no existe
    if _CONNINFO is None:
        conninfo = f"dbname={database} user={user} password={password} host={host} port={port} sslmode={sslmode}"
    else:
        conninfo = _CONNINFO

    # Si el pool está inicializado, devolver un context manager de conexión del pool
    if _POOL is not None:
        return _POOL.connection()

    # Si no hay pool (modo local/script), crear conexión directa
    return psycopg.connect(conninfo)
