# Imagen base de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app/ ./app/

# Exponer un puerto por documentación (Render asigna el puerto en runtime)
EXPOSE 8000

# Comando para ejecutar la aplicación
# Usamos el shell form para permitir que uvicorn lea la variable $PORT que Render asigna.
# Si $PORT no está definida, uvicorn usará 8000 por defecto.
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

