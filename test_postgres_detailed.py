#!/usr/bin/env python3
"""
Script para probar la conexión a Supabase PostgreSQL con parámetros detallados
"""

import os
from dotenv import load_dotenv
import psycopg2

# Cargar variables de entorno
load_dotenv()

def test_connection():
    # Construir DSN con parámetros adicionales
    params = {
        'dbname': os.getenv('PG_DATABASE'),
        'user': os.getenv('PG_USER'),
        'password': os.getenv('PG_PASSWORD'),
        'host': os.getenv('PG_HOST'),
        'port': os.getenv('PG_PORT'),
        'sslmode': 'require',
        'connect_timeout': 10
    }
    
    print("\nIntentando conectar a Supabase PostgreSQL con:")
    for k, v in params.items():
        if k != 'password':
            print(f"{k}: {v}")
    print("password: ***********")
    
    try:
        # Intentar conexión
        print("\nEstableciendo conexión...")
        conn = psycopg2.connect(**params)
        
        print("¡Conexión exitosa!")
        
        # Probar una consulta simple
        with conn.cursor() as cur:
            print("\nEjecutando consulta de prueba...")
            cur.execute('SELECT version();')
            version = cur.fetchone()
            print(f"Versión PostgreSQL: {version[0]}")
            
        conn.close()
        print("\nConexión cerrada correctamente")
        
    except Exception as e:
        print(f"\n❌ Error de conexión:")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Detalle: {str(e)}")
        
        # Sugerencias basadas en el error
        if "connection timed out" in str(e).lower():
            print("\nSugerencias:")
            print("1. Verifica que la IP esté en la whitelist de Supabase")
            print("2. Intenta usar el Connection Pooler (puerto 6543)")
            print("3. Comprueba si hay un firewall bloqueando la conexión")
        elif "password authentication failed" in str(e):
            print("\nSugerencia: Verifica las credenciales")
        elif "ssl" in str(e).lower():
            print("\nSugerencia: Ajusta la configuración SSL")

if __name__ == '__main__':
    test_connection()