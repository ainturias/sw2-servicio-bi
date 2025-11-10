# Servicio de Business Intelligence - Agencia de Viajes

Microservicio de Business Intelligence (BI) que proporciona KPIs, métricas y análisis de datos en tiempo real para una agencia de viajes. Sincroniza datos automáticamente desde MongoDB Atlas a PostgreSQL (Supabase) y expone una API REST con FastAPI.

## 🚀 Características

- **🔄 Sincronización en Tiempo Real**: MongoDB Change Streams actualiza PostgreSQL automáticamente (< 3 segundos)
- **📊 Dashboard BI**: Resumen ejecutivo con KPIs principales y tendencias
- **📈 7 KPIs de Negocio**: Margen bruto, tasa de conversión, cancelación, CSAT, top destinos, tendencias
- **🐳 Docker Ready**: Imagen Docker publicable para Kubernetes
- **☁️ Cloud Native**: Desplegado en Render + Supabase + MongoDB Atlas
- **📁 Export CSV**: Exportación de ventas con filtros de fecha
- **🔍 Filtros Avanzados**: Todos los endpoints soportan filtros por rango de fechas

## 📋 Stack Tecnológico

- **API**: FastAPI 0.104.1
- **Base de Datos**: 
  - PostgreSQL (Supabase) - Data Warehouse
  - MongoDB Atlas - Base de datos operacional
- **Pool de Conexiones**: psycopg 3.2.3 + psycopg-pool 3.2.3
- **Sincronización**: MongoDB Change Streams (pymongo 4.10.1)
- **Deployment**: Render.com (Docker runtime)
- **Containerización**: Docker + Kubernetes ready

## 🏗️ Estructura del Proyecto

```
servicio-bi/
├── app/
│   ├── main.py           # API FastAPI con 13 endpoints
│   ├── db.py             # Pool de conexiones PostgreSQL
│   ├── etl.py            # ETL MongoDB → PostgreSQL
│   └── realtime_sync.py  # Change Streams en tiempo real
├── Dockerfile            # Imagen Docker optimizada
├── docker-compose.yml    # Testing local
├── k8s-deployment.yaml   # Deployment para Kubernetes
├── requirements.txt      # Dependencias Python
├── Procfile             # Comando para Render
├── .dockerignore        # Optimización de builds
├── DOCKER_KUBERNETES.md # Guía Docker/K8s
├── DEPLOY_RENDER.md     # Guía de despliegue
└── README.md            # Este archivo
```

## ⚙️ Instalación Local

### 1. Clonar repositorio
```bash
git clone https://github.com/ainturias/sw2-servicio-bi.git
cd sw2-servicio-bi
```

### 2. Configurar variables de entorno

Crea archivo `.env` basado en `.env.example`:

```env
# MongoDB Atlas
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net
MONGO_DATABASE=agencia_viajes

# PostgreSQL (Supabase Transaction Pooler)
PG_DATABASE=postgres
PG_USER=postgres.xxxxxxxxxxxxx
PG_PASSWORD=tu_password
PG_HOST=aws-1-us-east-2.pooler.supabase.com
PG_PORT=6543
PG_SSLMODE=require
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecutar servicio
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Accede a:
- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs
- Health check: http://localhost:8000/health


## 🔄 Sincronización en Tiempo Real

El servicio incluye sincronización automática mediante **MongoDB Change Streams**.

### ¿Cómo funciona?

1. **Monitoreo Activo**: Escucha cambios en 6 colecciones de MongoDB
2. **Detección Inmediata**: INSERT, UPDATE, DELETE detectados en < 1 segundo
3. **Sincronización Automática**: Ejecuta ETL automáticamente al detectar cambios
4. **Actualización PostgreSQL**: Datos disponibles en 2-3 segundos

### Colecciones monitoreadas

- `clientes` (con lookup a `usuarios`)
- `agentes`
- `servicios`
- `paquetes_turisticos` (desde `paquetesTuristicos`)
- `ventas`
- `detalle_venta` (desde `detalleVenta`)

### Logs de sincronización

Al iniciar el servicio verás:
```
🚀 Iniciando aplicación...
✅ Pool de PostgreSQL inicializado
✅ Conectado a MongoDB para sincronización en tiempo real
👀 Iniciando monitoreo de cambios en base de datos: agencia_viajes
🔄 Monitoreo activo. Esperando cambios en MongoDB...
✅ Sincronización en tiempo real activada
```

Al detectar un cambio:
```
🔔 Cambio detectado: insert en clientes
🔄 Iniciando sincronización de datos...
✅ Sincronización completada exitosamente
```

### Endpoints de control

```bash
# Ver estado de sincronización
GET /sync/status

# Reiniciar sincronización (si se detiene)
POST /sync/restart

# Ejecutar sincronización manual completa
POST /sync/once
```

## 📊 Endpoints API

### 🏥 Health & Sync (5 endpoints)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Estado del servicio |
| `/health/pool` | GET | Diagnóstico del pool de conexiones |
| `/sync/status` | GET | Estado de la sincronización en tiempo real |
| `/sync/restart` | POST | Reiniciar sincronización manualmente |
| `/sync/once` | POST | Ejecutar sincronización completa manual |

### 📈 Dashboard (1 endpoint)

| Endpoint | Método | Descripción | Parámetros |
|----------|--------|-------------|------------|
| `/dashboard/resumen` | GET | Resumen ejecutivo con KPIs, top destinos y tendencias | `fecha_inicio`, `fecha_fin` (opcional) |

**Respuesta del dashboard:**
```json
{
  "periodo": {
    "inicio": "2025-01-01",
    "fin": "2025-01-31"
  },
  "kpis": {
    "total_clientes": 8,
    "total_ventas_confirmadas": 1,
    "total_monto_vendido": 200.0,
    "tasa_cancelacion": 0.0
  },
  "top_destinos": [
    {"destino": "La Paz", "ingresos": 200.0}
  ],
  "tendencia_reservas_por_dia": [
    {"fecha": "2025-11-06", "cantidad_reservas": 1}
  ]
}
```

### 📊 KPIs (4 endpoints)

| Endpoint | Descripción | Parámetros |
|----------|-------------|------------|
| `/kpi/margen-bruto` | Margen de ganancia (ingresos - costos) / ingresos | `fecha_inicio`, `fecha_fin` |
| `/kpi/tasa-conversion` | % ventas confirmadas / total ventas | `fecha_inicio`, `fecha_fin` |
| `/kpi/tasa-cancelacion` | % ventas canceladas / total ventas | `fecha_inicio`, `fecha_fin` |
| `/kpi/csat-promedio` | Promedio de satisfacción del cliente (1-5) | `fecha_inicio`, `fecha_fin` |

### 🌍 Analytics (1 endpoint)

| Endpoint | Descripción | Parámetros |
|----------|-------------|------------|
| `/analytics/top-destinos` | Top N destinos por ingresos | `limit=5`, `fecha_inicio`, `fecha_fin` |

### 📁 Export (1 endpoint)

| Endpoint | Descripción | Parámetros |
|----------|-------------|------------|
| `/export/ventas.csv` | Exportar ventas a CSV | `fecha_inicio`, `fecha_fin` |

### � Debug (1 endpoint)

| Endpoint | Descripción |
|----------|-------------|
| `/debug/mongo-counts` | Comparar conteos MongoDB vs PostgreSQL |

---

**Total: 13 endpoints operacionales**

## 🐳 Docker y Kubernetes

### Construir imagen Docker

```bash
# Construir imagen local
docker build -t servicio-bi:local .

# Ejecutar localmente
docker run -p 8000:8000 --env-file .env servicio-bi:local
```

### Docker Compose (testing local)

```bash
# Levantar servicio BI conectado a bases de datos en la nube
docker-compose up

# Ver logs
docker-compose logs -f servicio-bi

# Detener
docker-compose down
```

### Publicar en Docker Hub (para Kubernetes)

```bash
# 1. Login en Docker Hub
docker login

# 2. Construir y etiquetar
docker build -t tu_usuario/servicio-bi:latest .

# 3. Publicar
docker push tu_usuario/servicio-bi:latest
```

### Deployment en Kubernetes

Ver archivo `k8s-deployment.yaml` y guía completa en `DOCKER_KUBERNETES.md`.

```bash
# Aplicar deployment
kubectl apply -f k8s-deployment.yaml

# Verificar
kubectl get pods
kubectl get services
```

## ☁️ Despliegue en Producción (Render)

El servicio está desplegado en:
- **URL**: https://sw2-servicio-bi.onrender.com
- **Documentación**: https://sw2-servicio-bi.onrender.com/docs
- **Health**: https://sw2-servicio-bi.onrender.com/health

Ver guía completa en `DEPLOY_RENDER.md`.

### Auto-deploy desde GitHub

Cada push a `main` dispara un redespliegue automático en Render.

## 📝 Variables de Entorno

| Variable | Descripción | Requerido | Default |
|----------|-------------|-----------|---------|
| `MONGO_URI` | URI de MongoDB Atlas | ✅ | - |
| `MONGO_DATABASE` | Nombre de la base de datos MongoDB | ✅ | `agencia_viajes` |
| `PG_DATABASE` | Nombre de la base de datos PostgreSQL | ✅ | `postgres` |
| `PG_USER` | Usuario de PostgreSQL (Supabase) | ✅ | - |
| `PG_PASSWORD` | Contraseña de PostgreSQL | ✅ | - |
| `PG_HOST` | Host de PostgreSQL Pooler | ✅ | - |
| `PG_PORT` | Puerto del Transaction Pooler | ❌ | `6543` |
| `PG_SSLMODE` | Modo SSL | ❌ | `require` |


## 🗄️ Modelo de Datos

### PostgreSQL (Data Warehouse - Supabase)

6 tablas principales con relaciones optimizadas para analytics:

```
clientes
├── id (PK)
├── origen_id (UNIQUE) ← ID de MongoDB
├── nombre
├── email
├── telefono
└── fecha_registro

agentes
├── id (PK)
├── origen_id (UNIQUE)
├── nombre
├── email
└── telefono

servicios
├── id (PK)
├── origen_id (UNIQUE)
├── destino_ciudad
├── destino_pais
└── precio_costo

paquetes_turisticos
├── id (PK)
├── origen_id (UNIQUE)
├── destino_principal
└── precio_total_venta

ventas
├── id (PK)
├── origen_id (UNIQUE)
├── cliente_id (FK → clientes)
├── agente_id (FK → agentes)
├── estado (confirmada, cancelada, pendiente)
├── monto
├── fecha_venta
└── puntuacion_satisfaccion (1-5)

detalle_venta
├── id (PK)
├── origen_id (UNIQUE)
├── venta_id (FK → ventas)
├── servicio_id (FK → servicios)
├── paquete_id (FK → paquetes_turisticos)
├── cantidad
├── precio_unitario
└── subtotal
```

### MongoDB (Base Operacional - Atlas)

Colecciones monitoreadas por Change Streams:

- `usuarios` - Datos de autenticación y perfil
- `clientes` - Info adicional del cliente (join con usuarios)
- `agentes` - Agentes de ventas
- `servicios` - Servicios turísticos individuales
- `paquetesTuristicos` - Paquetes combinados
- `ventas` - Transacciones
- `detalleVenta` - Líneas de detalle de cada venta

## 🎯 KPIs Implementados

| KPI | Fórmula | Endpoint |
|-----|---------|----------|
| **Total Clientes** | COUNT(clientes) | `/dashboard/resumen` |
| **Ventas Confirmadas** | COUNT(ventas WHERE estado != 'cancelada') | `/dashboard/resumen` |
| **Monto Total Vendido** | SUM(ventas.monto WHERE estado != 'cancelada') | `/dashboard/resumen` |
| **Tasa de Cancelación** | (canceladas / total) × 100 | `/dashboard/resumen`, `/kpi/tasa-cancelacion` |
| **Top 5 Destinos** | GROUP BY destino, SUM(ingresos) ORDER BY DESC LIMIT 5 | `/dashboard/resumen`, `/analytics/top-destinos` |
| **Tendencia Reservas** | GROUP BY DATE(fecha_venta), COUNT(*) | `/dashboard/resumen` |
| **Margen Bruto** | ((ingresos - costos) / ingresos) × 100 | `/kpi/margen-bruto` |
| **Tasa de Conversión** | (confirmadas / total) × 100 | `/kpi/tasa-conversion` |
| **CSAT Promedio** | AVG(puntuacion_satisfaccion) | `/kpi/csat-promedio` |

**Total: 7 KPIs operacionales**

## 🧪 Testing

### Probar en local

```bash
# 1. Levantar servicio
uvicorn app.main:app --reload

# 2. Probar endpoints
curl http://localhost:8000/health
curl http://localhost:8000/dashboard/resumen
curl http://localhost:8000/debug/mongo-counts
```

### Probar en producción

```bash
# Dashboard completo
curl https://sw2-servicio-bi.onrender.com/dashboard/resumen

# Dashboard con filtro de fechas
curl "https://sw2-servicio-bi.onrender.com/dashboard/resumen?fecha_inicio=2025-01-01&fecha_fin=2025-01-31"

# Estado de sincronización
curl https://sw2-servicio-bi.onrender.com/sync/status

# Top 10 destinos
curl "https://sw2-servicio-bi.onrender.com/analytics/top-destinos?limit=10"

# Export CSV
curl "https://sw2-servicio-bi.onrender.com/export/ventas.csv" -o ventas.csv
```

### Documentación interactiva

Accede a la interfaz Swagger:
- Local: http://localhost:8000/docs
- Producción: https://sw2-servicio-bi.onrender.com/docs

## 🐛 Troubleshooting

### Error: "Pool de conexiones no inicializado"
```bash
# Solución: Verificar que init_pool() se ejecutó en startup
curl http://localhost:8000/health/pool
```

### Error: "Sincronización no activa"
```bash
# Solución: Reiniciar sincronización
curl -X POST http://localhost:8000/sync/restart
```

### Error: "MONGO_URI no configurada"
```bash
# Solución: Verificar variables de entorno
echo $MONGO_URI  # Linux/Mac
echo $env:MONGO_URI  # Windows PowerShell
```

### Verificar sincronización MongoDB ↔ PostgreSQL
```bash
# Ver diferencias entre MongoDB y PostgreSQL
curl http://localhost:8000/debug/mongo-counts
```

**Resultado esperado:**
```json
{
  "status": "success",
  "collections": {
    "clientes": {
      "mongo": 8,
      "postgres": 8,
      "diferencia": 0,
      "sincronizado": true
    },
    "ventas": {
      "mongo": 1,
      "postgres": 1,
      "diferencia": 0,
      "sincronizado": true
    }
  }
}
```

## 📚 Documentación Adicional

- `DOCKER_KUBERNETES.md` - Guía completa de Docker y Kubernetes
- `DEPLOY_RENDER.md` - Guía de despliegue en Render.com
- `.env.example` - Template de variables de entorno

## 🎓 Arquitectura

```
┌─────────────────────────────────────────┐
│  FRONTEND (Next.js)                     │
│  - Dashboard BI                         │
│  - Consume API REST                     │
└──────────────┬──────────────────────────┘
               │ HTTP/REST
               ↓
┌─────────────────────────────────────────┐
│  SERVICIO BI (FastAPI)                  │
│  - Render.com                           │
│  - 13 Endpoints REST                    │
│  - Pool de conexiones                   │
└──┬────────────────────────────────────┬─┘
   │                                    │
   │ Change Streams                     │ Queries SQL
   ↓                                    ↓
┌──────────────────┐        ┌──────────────────┐
│  MongoDB Atlas   │        │  PostgreSQL      │
│  - 7 colecciones │  ETL   │  (Supabase)      │
│  - Operacional   │ ────→  │  - 6 tablas      │
│                  │        │  - Analytics     │
└──────────────────┘        └──────────────────┘
```

## ✅ Checklist de Cumplimiento

### Requisitos del Documento

- ✅ Tarjetas con cantidad de clientes
- ✅ Tarjetas con ventas confirmadas
- ✅ Tarjetas con monto vendido
- ✅ Dashboards con filtros por fechas
- ✅ Export CSV
- ✅ Endpoints para módulo IA (JSON)

### KPIs Requeridos

- ✅ Margen Bruto de Ganancia
- ✅ Tasa de conversión de reservas
- ✅ Tasa de cancelación
- ✅ Top destinos más pedidos

### Tecnologías

- ✅ Python (FastAPI)
- ✅ PostgreSQL (Supabase)
- ✅ MongoDB (Atlas)
- ✅ Docker
- ✅ Kubernetes ready

## 🚀 Producción

**URL Servicio:** https://sw2-servicio-bi.onrender.com

**Estado Actual:**
- ✅ Desplegado en Render
- ✅ Sincronización en tiempo real activa
- ✅ 8 clientes sincronizados
- ✅ 1 venta activa ($200)
- ✅ Pool de conexiones operacional
- ✅ Docker runtime

## 👥 Integración con Frontend

El frontend puede consumir la API usando fetch/axios:

```javascript
// Ejemplo en React/Next.js
const Dashboard = () => {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    // Polling cada 30 segundos para datos actualizados
    const fetchData = () => {
      fetch('https://sw2-servicio-bi.onrender.com/dashboard/resumen')
        .then(res => res.json())
        .then(data => setData(data));
    };
    
    fetchData();
    const interval = setInterval(fetchData, 30000);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div>
      <h1>Clientes: {data?.kpis.total_clientes}</h1>
      <h1>Ventas: {data?.kpis.total_ventas_confirmadas}</h1>
      <h1>Monto: ${data?.kpis.total_monto_vendido}</h1>
    </div>
  );
};
```

## 📄 Licencia

Proyecto Académico - Software 2  
Universidad: [U.A.G.R.M]  
Fecha: Noviembre 2025

