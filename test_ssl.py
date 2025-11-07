#!/usr/bin/env python3
"""
Script para probar la conexión a Supabase PostgreSQL con SSL
"""

import os
from dotenv import load_dotenv
import psycopg2

# Cargar variables de entorno
load_dotenv()

def test_connection():
    # Construir DSN con configuración SSL
    params = {
        'dbname': os.getenv('PG_DATABASE'),
        'user': os.getenv('PG_USER'),
        'password': os.getenv('PG_PASSWORD'),
        'host': os.getenv('PG_HOST'),
        'port': os.getenv('PG_PORT'),
        'sslmode': 'require',
        'connect_timeout': 30
    }
    
    print("\nIntentando conectar a Supabase PostgreSQL con SSL:")
    for k, v in params.items():
        if k != 'password':
            print(f"{k}: {v}")
    print("password: ***********")
    
    try:
        print("\nEstableciendo conexión...")
        conn = psycopg2.connect(**params)
        
        print("¡Conexión exitosa!")
        
        # Verificar SSL
        cur = conn.cursor()
        cur.execute("SHOW ssl;")
        ssl_status = cur.fetchone()[0]
        print(f"\nEstado SSL: {ssl_status}")
        
        # Verificar versión
        cur.execute('SELECT version();')
        version = cur.fetchone()[0]
        print(f"Versión PostgreSQL: {version}")
        
        # Verificar usuario actual
        cur.execute('SELECT current_user;')
        user = cur.fetchone()[0]
        print(f"Usuario conectado: {user}")
        
        conn.close()
        print("\nConexión cerrada correctamente")
        
    except Exception as e:
        print(f"\n❌ Error de conexión:")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Detalle: {str(e)}")
        
        if "SSL SYSCALL error: EOF detected" in str(e):
            print("\nSugerencia: El servidor requiere SSL pero hay un problema con la configuración SSL")
        elif "connection timed out" in str(e):
            print("\nSugerencias:")
            print("1. Verifica que no haya un firewall bloqueando la conexión")
            print("2. Intenta usar el Connection Pooler (puerto 6543)")
        elif "password authentication failed" in str(e):
            print("\nSugerencia: Verifica las credenciales")

if __name__ == '__main__':
    test_connection()