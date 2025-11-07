import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
SSLMODE = os.getenv("sslmode", "require")

print("\nIntentando conectar con:")
print(f"Host: {HOST}")
print(f"Port: {PORT}")
print(f"Database: {DBNAME}")
print(f"User: {USER}")
print(f"SSL Mode: {SSLMODE}")
print("Password: ***********")

# Connect to the database
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        sslmode=SSLMODE,
        connect_timeout=30
    )
    print("\n¡Conexión exitosa!")
    
    # Create a cursor to execute SQL queries
    cursor = connection.cursor()
    
    # Check SSL
    cursor.execute("SHOW ssl;")
    ssl_status = cursor.fetchone()[0]
    print(f"SSL Status: {ssl_status}")
    
    # Example query
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("Hora actual en el servidor:", result)

    # Close the cursor and connection
    cursor.close()
    connection.close()
    print("Conexión cerrada.")

except Exception as e:
    print(f"\nError de conexión: {e}")
    
    # Sugerencias basadas en el error
    if "connection timed out" in str(e).lower():
        print("\nSugerencias:")
        print("1. La conexión está tardando demasiado. Como estás en IPv4, intenta:")
        print("   - Usar el Session Pooler (puerto 6543)")
        print("   - O comprar el add-on IPv4 en Supabase")
    elif "password authentication failed" in str(e):
        print("\nSugerencia: Verifica las credenciales en el panel de Supabase")
    elif "ssl" in str(e).lower():
        print("\nSugerencia: Asegúrate de que sslmode=require está configurado")