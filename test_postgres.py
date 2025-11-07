#!/usr/bin/env python3
"""
Script para probar la conexión a Supabase PostgreSQL
"""

import os
from dotenv import load_dotenv
import psycopg2

# Cargar variables de entorno
load_dotenv()

def test_connection():
    # Obtener variables de entorno
    params = {
        'dbname': os.getenv('PG_DATABASE'),
        'user': os.getenv('PG_USER'),
        'password': os.getenv('PG_PASSWORD'),
        'host': os.getenv('PG_HOST'),
        'port': os.getenv('PG_PORT'),
        'sslmode': os.getenv('PG_SSLMODE')
    }
    
    print("\nIntentando conectar a Supabase PostgreSQL con:")
    for k, v in params.items():
        if k != 'password':
            print(f"{k}: {v}")
    print("password: ***********")
    
    try:
        # Intentar conexión
        conn = psycopg2.connect(**params)
        
        print("\n¡Conexión exitosa!")
        
        # Probar una consulta simple
        with conn.cursor() as cur:
            cur.execute('SELECT version();')
            version = cur.fetchone()
            print(f"\nVersión PostgreSQL: {version[0]}")
            
            # Listar tablas
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            if tables:
                print("\nTablas encontradas:")
                for table in tables:
                    print(f"- {table[0]}")
            else:
                print("\nNo se encontraron tablas en el esquema public")
        
        conn.close()
        print("\nConexión cerrada correctamente")
        
    except Exception as e:
        print(f"\n❌ Error de conexión:")
        print(f"Detalle: {str(e)}")
        if "SSL off" in str(e):
            print("\nSugerencia: Asegúrate de que PG_SSLMODE esté configurado como 'require'")
        elif "password authentication failed" in str(e):
            print("\nSugerencia: Verifica las credenciales (usuario/contraseña)")
        elif "connection timed out" in str(e):
            print("\nSugerencia: Verifica si necesitas usar el Session Pooler para IPv4")

if __name__ == '__main__':
    test_connection()