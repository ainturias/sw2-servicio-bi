import os
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def init_database():
    # Leer el contenido del archivo SQL
    with open('init.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # Conectar a PostgreSQL
    conn = psycopg2.connect(
        dbname=os.getenv("dbname", "postgres"),
        user=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host", "aws-1-us-east-2.pooler.supabase.com"),
        port=os.getenv("port", "6543"),
        sslmode='require'
    )
    
    # Crear un cursor y ejecutar el script
    cur = conn.cursor()
    try:
        cur.execute(sql_script)
        conn.commit()
        print("Base de datos inicializada correctamente")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    init_database()