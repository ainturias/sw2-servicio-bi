import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables exactly as shown in Supabase example
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

print("\nIntentando conectar con Transaction Pooler:")
print(f"Host: {HOST}")
print(f"Port: {PORT}")
print(f"Database: {DBNAME}")
print(f"User: {USER}")
print("Password: ***********")

# Connect to the database
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        sslmode='require',
        connect_timeout=30
    )
    print("\n¡Conexión exitosa!")
    
    # Create a cursor to execute SQL queries
    cursor = connection.cursor()
    
    # Check connection info
    cursor.execute("SELECT current_database(), current_user, version();")
    db, user, version = cursor.fetchone()
    print(f"\nBase de datos: {db}")
    print(f"Usuario: {user}")
    print(f"Versión: {version}")
    
    # Example query
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print(f"\nHora actual en el servidor: {result[0]}")

    # Close the cursor and connection
    cursor.close()
    connection.close()
    print("\nConexión cerrada correctamente.")

except Exception as e:
    print(f"\nError de conexión: {e}")
    
    if "password authentication failed" in str(e):
        print("\nSugerencia: Verifica que el usuario incluya el sufijo del proyecto")
        print("El formato debe ser: postgres.miosyngnmfawuyazcvhk")