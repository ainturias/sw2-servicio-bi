# Servicio de Business Intelligence - Agencia de Viajes

Este es el microservicio de Business Intelligence (BI) para la agencia de viajes, diseñado para proporcionar KPIs, métricas y análisis de datos a través de una API REST con sincronización en tiempo real.

## 🚀 Características

- **🔄 Sincronización en Tiempo Real**: Usa MongoDB Change Streams para actualizar PostgreSQL automáticamente cuando hay cambios
- **ETL Automatizado**: Sincronización inicial de datos desde MongoDB Atlas a PostgreSQL
- **API REST**: Endpoints FastAPI para consulta de KPIs y métricas
- **KPIs de Negocio**: 
  - Margen bruto
  - Tasa de conversión
  - Tasa de cancelación
  - Satisfacción del cliente (CSAT)
- **Análisis de Datos**:
  - Dashboard con métricas principales siempre actualizados
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
│   ├── main.py           # Endpoints FastAPI
│   ├── db.py            # Conexión PostgreSQL
│   ├── etl.py           # Script ETL MongoDB → PostgreSQL
│   └── realtime_sync.py # Sincronización en tiempo real
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── init.sql             # Esquema PostgreSQL
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

## � Sincronización en Tiempo Real

**¡NUEVA FUNCIONALIDAD!** El servicio ahora incluye sincronización automática en tiempo real.

### ¿Cómo funciona?

Cuando inicias el servidor FastAPI, automáticamente se activa un proceso que:

1. **Monitorea MongoDB**: Usa MongoDB Change Streams para detectar cambios en tiempo real
2. **Sincroniza Automáticamente**: Cuando detecta un INSERT, UPDATE o DELETE en MongoDB, ejecuta la sincronización inmediatamente
3. **Mantiene Datos Actualizados**: Los KPIs y dashboards siempre muestran información actual

### Colecciones monitoreadas

- `clientes`
- `agentes`
- `servicios`
- `paquetes_turisticos`
- `ventas`
- `detalle_venta`

### Ventajas

✅ **Dashboards siempre actualizados**: No necesitas ejecutar ETL manualmente  
✅ **Respuesta inmediata**: Los cambios en MongoDB se reflejan en PostgreSQL en segundos  
✅ **Transparente**: No requiere configuración adicional, funciona automáticamente  
✅ **Ideal para integración**: Perfecto cuando el frontend/backend necesita datos en tiempo real

### Iniciar el servidor con sincronización

```bash
# La sincronización se inicia automáticamente al ejecutar:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verás en los logs:
```
🚀 Iniciando aplicación...
✅ Conectado a MongoDB para sincronización en tiempo real
👀 Iniciando monitoreo de cambios en base de datos: agencia_viajes
🔄 Monitoreo activo. Esperando cambios en MongoDB...
✅ Sincronización en tiempo real activada
```

### Probar la sincronización

```bash
# Ejecutar script de prueba que inserta un cliente en MongoDB
# y verifica que se sincroniza a PostgreSQL
python test_realtime_sync.py
```

### ⚠️ Plan B: Reiniciar sincronización manualmente

Si por alguna razón la sincronización se detiene, puedes reiniciarla usando:

```bash
# Desde terminal
curl -X POST http://localhost:8000/sync/restart

# O desde el navegador, ve a:
# http://localhost:8000/docs
# Y ejecuta el endpoint POST /sync/restart
```

## � Endpoints Disponibles

### Health Check
- `GET /health` - Estado del servicio
- `GET /sync/status` - Estado de la sincronización en tiempo real
- `POST /sync/restart` - Reiniciar la sincronización manualmente (útil si se detiene)

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

### Ejecutar suite completa de pruebas

El proyecto incluye un script de pruebas automatizado que valida todos los endpoints:

```bash
# Asegúrate de que el servidor esté corriendo
uvicorn app.main:app --host 127.0.0.1 --port 8001

# En otra terminal, ejecuta las pruebas
python test_completo.py
```

El script probará:
- ✅ Health check y estado de sincronización
- ✅ Dashboard con y sin filtros
- ✅ Todos los KPIs (margen bruto, conversión, cancelación, CSAT)
- ✅ Analytics (top destinos)
- ✅ Exportación CSV
- ✅ Reinicio manual de sincronización

**Resultado esperado:** 11/11 pruebas exitosas (100%)

### Probar endpoints manualmente

```bash
# Health check
curl http://localhost:8000/health

# Estado de sincronización
curl http://localhost:8000/sync/status

# Dashboard resumen
curl "http://localhost:8000/dashboard/resumen?fecha_inicio=2024-01-01&fecha_fin=2024-01-31"

# Margen bruto
curl "http://localhost:8000/kpi/margen-bruto?fecha_inicio=2024-01-01&fecha_fin=2024-01-31"

# Top destinos
curl "http://localhost:8000/analytics/top-destinos?limit=5"

# Export CSV
curl "http://localhost:8000/export/ventas.csv?fecha_inicio=2024-01-01&fecha_fin=2024-01-31" -o ventas.csv

# Reiniciar sincronización (si es necesario)
curl -X POST http://localhost:8000/sync/restart
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

