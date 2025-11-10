"""
Script de diagnóstico para entender por qué no se insertan clientes en PostgreSQL
"""
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
import psycopg

# Cargar variables de entorno
load_dotenv()

def main():
    print("=== DIAGNÓSTICO DE SINCRONIZACIÓN ===\n")
    
    # 1. Conectar a MongoDB
    print("1. Conectando a MongoDB...")
    mongo_uri = os.getenv("MONGO_URI")
    mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
    
    if not mongo_uri:
        print("❌ MONGO_URI no configurada")
        return
    
    mongo_client = MongoClient(mongo_uri)
    mongo_db = mongo_client[mongo_db_name]
    
    # Obtener clientes de MongoDB
    clientes = list(mongo_db.clientes.find())
    print(f"✅ Clientes en MongoDB: {len(clientes)}")
    
    if clientes:
        print(f"\n📄 Primer cliente MongoDB:")
        primer_cliente = clientes[0]
        print(f"   _id: {primer_cliente.get('_id')}")
        print(f"   nombre: {primer_cliente.get('nombre')}")
        print(f"   email: {primer_cliente.get('email')}")
        print(f"   telefono: {primer_cliente.get('telefono')}")
        print(f"   fechaRegistro: {primer_cliente.get('fechaRegistro')}")
    
    # 2. Conectar a PostgreSQL
    print("\n2. Conectando a PostgreSQL...")
    postgres_uri = os.getenv("POSTGRES_URI")
    
    if not postgres_uri:
        print("❌ POSTGRES_URI no configurada")
        return
    
    try:
        conn = psycopg.connect(postgres_uri)
        print("✅ Conectado a PostgreSQL")
        
        # Verificar tabla clientes
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clientes")
            count = cur.fetchone()[0]
            print(f"✅ Clientes en PostgreSQL: {count}")
            
            # Intentar insertar el primer cliente manualmente
            if clientes:
                print("\n3. Intentando insertar primer cliente...")
                cliente = clientes[0]
                
                try:
                    cur.execute("""
                        INSERT INTO clientes (origen_id, nombre, email, telefono, fecha_registro)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (origen_id) 
                        DO UPDATE SET
                            nombre = EXCLUDED.nombre,
                            email = EXCLUDED.email,
                            telefono = EXCLUDED.telefono
                        RETURNING id
                    """, (
                        str(cliente['_id']),
                        cliente.get('nombre', ''),
                        cliente.get('email', ''),
                        cliente.get('telefono')
                    ))
                    
                    result = cur.fetchone()
                    conn.commit()
                    print(f"✅ Cliente insertado con id: {result[0]}")
                    
                    # Verificar que se insertó
                    cur.execute("SELECT COUNT(*) FROM clientes")
                    new_count = cur.fetchone()[0]
                    print(f"✅ Total clientes ahora: {new_count}")
                    
                except Exception as e:
                    conn.rollback()
                    print(f"❌ ERROR al insertar cliente:")
                    print(f"   Tipo: {type(e).__name__}")
                    print(f"   Mensaje: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ ERROR conectando a PostgreSQL:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        import traceback
        traceback.print_exc()
    
    mongo_client.close()
    print("\n=== FIN DEL DIAGNÓSTICO ===")

if __name__ == "__main__":
    main()
