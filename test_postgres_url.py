#!/usr/bin/env python3
"""
Script para probar la conexión a Supabase PostgreSQL usando URL directa
"""

import os
from dotenv import load_dotenv
import psycopg2

# Cargar variables de entorno
load_dotenv()

def test_connection():
    # Obtener DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    
    print("\nIntentando conectar a Supabase PostgreSQL usando URL directa")
    
    try:
        # Intentar conexión
        conn = psycopg2.connect(database_url)
        
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

if __name__ == '__main__':
    test_connection()