import os
import psycopg2
from dotenv import load_dotenv
from tabulate import tabulate

# Cargar variables de entorno
load_dotenv()

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("dbname", "postgres"),
        user=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host", "aws-1-us-east-2.pooler.supabase.com"),
        port=os.getenv("port", "6543"),
        sslmode='require'
    )

def print_table_data(conn, table_name):
    print(f"\n=== Datos en tabla {table_name} ===")
    cur = conn.cursor()
    try:
        # Obtener nombres de columnas
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position")
        columns = [row[0] for row in cur.fetchall()]
        
        # Obtener datos
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        
        if rows:
            print(tabulate(rows, headers=columns, tablefmt="grid"))
            print(f"Total registros: {len(rows)}")
        else:
            print("No hay datos en esta tabla")
            
    except Exception as e:
        print(f"Error al consultar {table_name}: {e}")
    finally:
        cur.close()

def main():
    conn = get_connection()
    try:
        tables = [
            'clientes',
            'agentes',
            'servicios',
            'paquetes_turisticos',
            'ventas',
            'detalle_venta'
        ]
        
        for table in tables:
            print_table_data(conn, table)
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()