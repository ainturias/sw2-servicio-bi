import os
import psycopg2
from psycopg2.extensions import connection
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()


def get_conn() -> connection:
    """
    Crea y retorna una conexión a PostgreSQL usando el Transaction Pooler de Supabase.
    
    Variables de entorno requeridas:
    - user: Usuario de PostgreSQL (formato: postgres.<proyecto_id>)
    - password: Contraseña de PostgreSQL
    - host: Host del pooler (aws-1-us-east-2.pooler.supabase.com)
    - port: Puerto del pooler (default: 6543)
    - dbname: Nombre de la base de datos (default: postgres)
    
    Returns:
        connection: Conexión a la base de datos PostgreSQL
        
    Raises:
        ValueError: Si faltan variables de entorno requeridas
        psycopg2.Error: Si hay un error al conectar con la base de datos
    """
    # Leer variables de entorno como están definidas en Supabase
    database = os.getenv("dbname", "postgres")
    user = os.getenv("user")
    password = os.getenv("password")
    host = os.getenv("host", "aws-1-us-east-2.pooler.supabase.com")
    port = os.getenv("port", "6543")
    sslmode = "require"  # Siempre requerido para Supabase
    
    # Validar variables requeridas
    if not database:
        raise ValueError("PG_DATABASE no está configurada")
    if not user:
        raise ValueError("PG_USER no está configurada")
    if not password:
        raise ValueError("PG_PASSWORD no está configurada")
    
    # Construir connection string con SSL mode
    conn_params = {
        "database": database,
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "sslmode": sslmode
    }
    
    # Crear y retornar la conexión
    return psycopg2.connect(**conn_params)
