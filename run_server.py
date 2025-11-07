import os
import subprocess
from dotenv import load_dotenv

def main():
    # Cargar variables de entorno
    load_dotenv()
    
    # Configurar variables de entorno para PostgreSQL
    os.environ["user"] = "postgres.rlxekplhjlrfqxxsukyf"
    os.environ["password"] = "GrV9R5HXGu9vr5E6"
    os.environ["host"] = "aws-1-us-east-2.pooler.supabase.com"
    os.environ["port"] = "6543"
    os.environ["dbname"] = "postgres"
    
    # Configurar PYTHONPATH
    os.environ["PYTHONPATH"] = "."
    
    # Iniciar el servidor
    subprocess.run(["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])

if __name__ == "__main__":
    main()