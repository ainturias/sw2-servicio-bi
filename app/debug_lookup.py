"""
Script para diagnosticar el problema del lookup MongoDB
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv
import json
from bson import ObjectId

load_dotenv()

def custom_json_encoder(obj):
    """Encoder personalizado para ObjectId y otros tipos BSON"""
    if isinstance(obj, ObjectId):
        return {"$oid": str(obj), "_type": "ObjectId"}
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def main():
    mongo_uri = os.getenv("MONGO_URI")
    mongo_db_name = os.getenv("MONGO_DATABASE", "agencia_viajes")
    
    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]
    
    print("=" * 80)
    print("DIAGNÓSTICO: LOOKUP MONGODB")
    print("=" * 80)
    
    # 1. Ver un cliente directo (sin lookup)
    print("\n1. CLIENTE SIN LOOKUP:")
    print("-" * 80)
    cliente_raw = db.clientes.find_one()
    if cliente_raw:
        print(json.dumps(cliente_raw, indent=2, default=custom_json_encoder))
        print(f"\nTipo de usuarioId: {type(cliente_raw.get('usuarioId'))}")
    
    # 2. Ver el usuario correspondiente
    print("\n2. USUARIO CORRESPONDIENTE:")
    print("-" * 80)
    if cliente_raw and 'usuarioId' in cliente_raw:
        usuario = db.usuarios.find_one({"_id": cliente_raw['usuarioId']})
        if usuario:
            print(json.dumps(usuario, indent=2, default=custom_json_encoder))
        else:
            print(f"❌ NO SE ENCONTRÓ usuario con _id = {cliente_raw['usuarioId']}")
            print(f"Tipo del usuarioId buscado: {type(cliente_raw['usuarioId'])}")
    
    # 3. Intentar lookup como lo hace el ETL
    print("\n3. LOOKUP COMO EN ETL:")
    print("-" * 80)
    pipeline = [
        {
            '$lookup': {
                'from': 'usuarios',
                'localField': 'usuarioId',
                'foreignField': '_id',
                'as': 'usuario'
            }
        },
        {
            '$unwind': {
                'path': '$usuario',
                'preserveNullAndEmptyArrays': False
            }
        },
        {
            '$limit': 1
        }
    ]
    
    resultado_lookup = list(db.clientes.aggregate(pipeline))
    print(f"Resultados del lookup: {len(resultado_lookup)}")
    
    if resultado_lookup:
        print("\n✅ LOOKUP EXITOSO:")
        cliente_con_usuario = resultado_lookup[0]
        print(json.dumps(cliente_con_usuario, indent=2, default=custom_json_encoder))
    else:
        print("\n❌ LOOKUP FALLÓ - NO TRAJO RESULTADOS")
        print("\nPOSIBLES CAUSAS:")
        print("1. El campo usuarioId en clientes es String pero _id en usuarios es ObjectId")
        print("2. El campo usuarioId en clientes no coincide con ningún _id en usuarios")
        print("3. Todos los clientes tienen usuarioId inválido")
        
        # Verificar tipos
        print("\nVERIFICANDO TIPOS DE DATOS:")
        print("-" * 80)
        
        sample_cliente = db.clientes.find_one()
        sample_usuario = db.usuarios.find_one()
        
        if sample_cliente:
            print(f"Tipo de clientes.usuarioId: {type(sample_cliente.get('usuarioId'))}")
        if sample_usuario:
            print(f"Tipo de usuarios._id: {type(sample_usuario.get('_id'))}")
        
        # Contar clientes sin lookup exitoso
        all_clientes = list(db.clientes.find({}, {"_id": 1, "usuarioId": 1}))
        print(f"\nTotal clientes: {len(all_clientes)}")
        
        clientes_con_lookup = list(db.clientes.aggregate(pipeline))
        print(f"Clientes con lookup exitoso: {len(clientes_con_lookup)}")
        print(f"Clientes SIN lookup exitoso: {len(all_clientes) - len(clientes_con_lookup)}")
    
    client.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
