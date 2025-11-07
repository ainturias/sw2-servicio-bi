# Servicio de Business Intelligence - Agencia de Viajes

Este es el microservicio de Business Intelligence (BI) para la agencia de viajes, diseñado para proporcionar KPIs, métricas y análisis de datos a través de una API REST.

## 🚀 Características

- **ETL Automatizado**: Sincronización de datos desde MongoDB Atlas a PostgreSQL
- **API REST**: Endpoints FastAPI para consulta de KPIs y métricas
- **KPIs de Negocio**: 
  - Margen bruto
  - Tasa de conversión
  - Tasa de cancelación
  - Satisfacción del cliente (CSAT)
- **Análisis de Datos**:
  - Dashboard con métricas principales
  - Top destinos por ingresos
  - Tendencias de reservas por día
- **Exportación**: Datos de ventas en formato CSV
- **Filtros**: Todos los endpoints soportan filtros por fecha
- **Docker**: Contenedorización para desarrollo y producción

## 📋 Requisitos

- Python 3.10+
- PostgreSQL (Supabase)
- MongoDB Atlas
- Docker y Docker Compose (opcional)

## 🏗️ Estructura del Proyecto

```
servicio-bi/
├── app/
│   ├── __init__.py
│   ├── main.py        # Endpoints FastAPI
│   ├── db.py         # Conexión PostgreSQL
│   └── etl.py        # Script ETL MongoDB → PostgreSQL
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── init.sql          # Esquema PostgreSQL
└── README.md
```

## ⚙️ Instalación

1. Clonar el repositorio
2. Crear archivo `.env` con las credenciales:

```env
# MongoDB
MONGO_URI=mongodb+srv://user:pass@host/db
MONGO_DATABASE=agencia_viajes

# PostgreSQL
user=postgres.xxxxx
password=xxxxx
host=aws-1-us-east-2.pooler.supabase.com
port=6543
dbname=postgres
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Inicializar base de datos:
```bash
python init_db.py
```

### 4. Ejecutar ETL manualmente

Para sincronizar datos desde MongoDB Atlas a PostgreSQL:

```bash
# Desde el directorio servicio-bi/
python -m app.etl
```

O si estás dentro del contenedor:

```bash
docker-compose exec servicio-bi python -m app.etl
```

## 📡 Endpoints Disponibles

### Health Check
- `GET /health` - Estado del servicio

### Dashboard
- `GET /dashboard/resumen?fecha_inicio=2024-01-01&fecha_fin=2024-01-31`
  - KPIs: total clientes, ventas confirmadas, monto vendido, tasa cancelación
  - Top 5 destinos por ingresos
  - Tendencia de reservas por día

### KPIs
- `GET /kpi/margen-bruto?fecha_inicio=2024-01-01&fecha_fin=2024-01-31`
- `GET /kpi/tasa-conversion?fecha_inicio=2024-01-01&fecha_fin=2024-01-31`
- `GET /kpi/tasa-cancelacion?fecha_inicio=2024-01-01&fecha_fin=2024-01-31`
- `GET /kpi/csat-promedio?fecha_inicio=2024-01-01&fecha_fin=2024-01-31`

### Analytics
- `GET /analytics/top-destinos?limit=5&fecha_inicio=2024-01-01&fecha_fin=2024-01-31`

### Export
- `GET /export/ventas.csv?fecha_inicio=2024-01-01&fecha_fin=2024-01-31`
  - Descarga CSV de ventas confirmadas con detalle

**Nota**: Todos los parámetros de fecha son opcionales. Si no se proporcionan, se consideran todos los datos.

## 🗄️ Estructura de Base de Datos

El script `init.sql` crea las siguientes tablas:

- `clientes` - Información de clientes
- `agentes` - Información de agentes de ventas
- `servicios` - Servicios turísticos (con destino_ciudad, destino_pais, precio_costo)
- `paquetes_turisticos` - Paquetes turísticos (con destino_principal, precio_total_venta)
- `ventas` - Ventas (con estado, fecha_venta, puntuacion_satisfaccion)
- `detalle_venta` - Detalles de cada venta (con servicio_id, paquete_id, subtotal)
- `pagos` - Pagos (opcional)

## 🔄 ETL

El script `app/etl.py` realiza:

1. **Extracción**: Desde MongoDB Atlas (colecciones: clientes, agentes, servicios, paquetes_turisticos, ventas, detalle_venta)
2. **Transformación**: 
   - Normaliza estados
   - Calcula costos estimados
   - Mapea destinos (ciudad/pais o destino_principal)
3. **Carga**: UPSERT en PostgreSQL usando `origen_id` para evitar duplicados

### Ejecutar ETL

```bash
# Asegúrate de tener las variables de entorno configuradas
export MONGO_URI="mongodb+srv://..."
export PG_DATABASE=agencia-viajes-bi
export PG_USER=postgres
export PG_PASSWORD=7550
export PG_HOST=localhost

# Ejecutar ETL
python -m app.etl
```

## 🐳 Producción

Para producción, usa un PostgreSQL gestionado (Neon, Supabase, ElephantSQL, Render):

1. Configura `PG_HOST` con el host del servicio gestionado
2. Configura `PG_SSLMODE=require`
3. Configura las demás variables según tu proveedor
4. Despliega el servicio (puedes usar el mismo Dockerfile)

## 📝 Variables de Entorno

| Variable | Descripción | Requerido | Default |
|----------|-------------|-----------|---------|
| `PG_DATABASE` | Nombre de la base de datos PostgreSQL | ✅ | - |
| `PG_USER` | Usuario de PostgreSQL | ✅ | - |
| `PG_PASSWORD` | Contraseña de PostgreSQL | ✅ | - |
| `PG_HOST` | Host de PostgreSQL | ✅ | `localhost` |
| `PG_PORT` | Puerto de PostgreSQL | ❌ | `5432` |
| `PG_SSLMODE` | Modo SSL (disable/require) | ❌ | `disable` |
| `MONGO_URI` | URI de conexión a MongoDB Atlas | ✅ | - |
| `MONGO_DATABASE` | Nombre de la base de datos MongoDB | ❌ | `agencia-viajes` |

## 🧪 Pruebas

### Probar endpoints manualmente

```bash
# Health check
curl http://localhost:8000/health

# Dashboard resumen
curl "http://localhost:8000/dashboard/resumen?fecha_inicio=2024-01-01&fecha_fin=2024-01-31"

# Margen bruto
curl "http://localhost:8000/kpi/margen-bruto?fecha_inicio=2024-01-01&fecha_fin=2024-01-31"

# Top destinos
curl "http://localhost:8000/analytics/top-destinos?limit=5"

# Export CSV
curl "http://localhost:8000/export/ventas.csv?fecha_inicio=2024-01-01&fecha_fin=2024-01-31" -o ventas.csv
```

## 📚 Estructura del Proyecto

```
servicio-bi/
├── app/
│   ├── main.py          # API FastAPI con todos los endpoints
│   ├── db.py            # Conexión a PostgreSQL
│   └── etl.py           # Script ETL MongoDB → PostgreSQL
├── init.sql             # DDL + datos de prueba + índices
├── requirements.txt     # Dependencias Python
├── Dockerfile           # Imagen Docker del servicio
├── docker-compose.yml   # Orquestación local (dev)
├── .env.example         # Ejemplo de variables de entorno
└── README.md            # Esta documentación
```

## ✅ Criterios de Aceptación

- ✅ `/health` OK
- ✅ `/dashboard/resumen` con filtros de fecha, cards, top destinos y tendencia
- ✅ Todos los endpoints KPI funcionando con filtros
- ✅ Export CSV funcionando
- ✅ `etl.py` ejecutable manualmente sin errores (inserta/actualiza)
- ✅ Código limpio y comentado

## 🐛 Troubleshooting

### Error de conexión a PostgreSQL
- Verifica que PostgreSQL esté corriendo
- Revisa las variables de entorno `PG_*`
- Para producción, asegúrate de usar `PG_SSLMODE=require`

### Error de conexión a MongoDB
- Verifica que `MONGO_URI` esté correctamente configurada
- Asegúrate de que tu IP esté en la whitelist de MongoDB Atlas
- Verifica que el usuario tenga permisos de lectura

### Verificar datos en MongoDB
Para verificar si hay datos en las colecciones de MongoDB:

```bash
# Desde el directorio servicio-bi/
python check_mongo.py
```

Este script mostrará el número de documentos en cada colección y un ejemplo si hay datos.

### El ETL no encuentra datos
- Verifica los nombres de las colecciones en MongoDB
- Revisa que las colecciones tengan datos
- Verifica los logs del ETL para ver qué colecciones se están procesando

## 📄 Licencia

Proyecto académico - Software 2

