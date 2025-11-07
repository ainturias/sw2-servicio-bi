"""
Script para probar la sincronización en tiempo real
Inserta un documento en MongoDB y verifica que se sincronice a PostgreSQL
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv
import time
from app.db import get_conn

# Cargar variables de entorno
load_dotenv()

def test_realtime_sync():
    """Probar la sincronización en tiempo real"""
    
    # Conectar a MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    mongo_db = os.getenv("MONGO_DATABASE", "agencia_viajes")
    
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client[mongo_db]
    
    print("🧪 Iniciando prueba de sincronización en tiempo real...")
    print("-" * 60)
    
    # 1. Contar clientes actuales en PostgreSQL
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clientes")
    count_before = cur.fetchone()[0]
    print(f"📊 Clientes en PostgreSQL antes: {count_before}")
    
    # 2. Insertar un nuevo cliente en MongoDB
    print("\n📝 Insertando nuevo cliente en MongoDB...")
    test_cliente = {
        "nombre": "Cliente Prueba Sync",
        "apellido": "Real Time",
        "email": "prueba.sync@test.com",
        "telefono": "+591 99999999",
        "pais": "Bolivia",
        "fecha_registro": "2024-11-07T10:00:00"
    }
    
    result = db.clientes.insert_one(test_cliente)
    print(f"✅ Cliente insertado en MongoDB con ID: {result.inserted_id}")
    
    # 3. Esperar a que se sincronice (dar tiempo al Change Stream)
    print("\n⏳ Esperando sincronización (10 segundos)...")
    time.sleep(10)
    
    # 4. Verificar si se sincronizó a PostgreSQL
    print("\n🔍 Verificando sincronización en PostgreSQL...")
    cur.execute("SELECT COUNT(*) FROM clientes")
    count_after = cur.fetchone()[0]
    print(f"📊 Clientes en PostgreSQL después: {count_after}")
    
    # 5. Buscar el cliente específico
    cur.execute("""
        SELECT nombre, apellido, email 
        FROM clientes 
        WHERE email = %s
    """, (test_cliente["email"],))
    
    cliente_sync = cur.fetchone()
    
    if cliente_sync:
        print(f"\n✅ ¡Sincronización exitosa!")
        print(f"   Nombre: {cliente_sync[0]} {cliente_sync[1]}")
        print(f"   Email: {cliente_sync[2]}")
    else:
        print(f"\n⚠️ El cliente no se encontró en PostgreSQL")
        print("   La sincronización puede tardar más tiempo o hay un problema")
    
    # Limpiar
    cur.close()
    conn.close()
    mongo_client.close()
    
    print("\n" + "-" * 60)
    print("🏁 Prueba completada")
    
    if count_after > count_before:
        print("✅ La sincronización está funcionando correctamente")
    else:
        print("❌ La sincronización no funcionó como se esperaba")


if __name__ == "__main__":
    test_realtime_sync()
