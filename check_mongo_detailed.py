from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def main():
    # Conectar a MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    
    print("\nListado de bases de datos disponibles:")
    print("=" * 50)
    dbs = client.list_database_names()
    for db in dbs:
        print(f"Base de datos: {db}")
        # Listar colecciones en cada base de datos
        collections = client[db].list_collection_names()
        if collections:
            print("  Colecciones:")
            for col in collections:
                count = client[db][col].count_documents({})
                print(f"  - {col}: {count} documentos")
        else:
            print("  No hay colecciones")
        print()
    
    print("=" * 50)
    print("\nDetalles de la base de datos actual:")
    print("=" * 50)
    current_db_name = os.getenv("MONGO_DATABASE", "agencia-viajes")
    print(f"Base de datos configurada: {current_db_name}")
    
    db = client[current_db_name]
    collections = db.list_collection_names()
    if collections:
        print("\nColecciones encontradas:")
        for col in collections:
            print(f"\nColección: {col}")
            # Mostrar un documento de ejemplo
            doc = db[col].find_one()
            if doc:
                print("Ejemplo de documento:")
                print(doc)
            else:
                print("Colección vacía")
    else:
        print("\nNo se encontraron colecciones en esta base de datos")

if __name__ == "__main__":
    main()