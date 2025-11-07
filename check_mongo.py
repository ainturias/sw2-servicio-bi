#!/usr/bin/env python3
"""
Script para verificar datos en las colecciones de MongoDB
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Cargar variables de entorno
load_dotenv()

def main():
    # Conectar a MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    mongo_db_name = os.getenv("MONGO_DATABASE", "agencia-viajes")
    
    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]
    
    # Colecciones a verificar
    collections = [
        'clientes', 'agentes', 'servicios', 
        'paquetes_turisticos', 'ventas', 'detalle_venta'
    ]
    
    print("\nEstado de las colecciones en MongoDB:")
    print("=" * 50)
    
    # Verificar cada colección
    for col_name in collections:
        try:
            count = db[col_name].count_documents({})
            print(f"Colección '{col_name}': {count} documentos")
            
            # Mostrar un ejemplo si hay documentos
            if count > 0:
                example = db[col_name].find_one()
                print("  Ejemplo de documento:")
                print("  " + str(example))
                print()
        except Exception as e:
            print(f"Error al verificar '{col_name}': {e}")
    
    print("=" * 50)

if __name__ == "__main__":
    main()