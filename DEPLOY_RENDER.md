# 🚀 Guía de Despliegue en Render

## Prerrequisitos
- ✅ Cuenta en Render (https://render.com)
- ✅ Cuenta conectada con GitHub
- ✅ Repositorio sw2-servicio-bi en GitHub

---

## 📋 Paso a Paso

### 1. Crear Nuevo Web Service

1. Ve a https://dashboard.render.com
2. Click en **"New +"** (arriba a la derecha)
3. Selecciona **"Web Service"**

### 2. Conectar Repositorio

1. Busca y selecciona: **`sw2-servicio-bi`**
2. Click en **"Connect"**

### 3. Configurar el Servicio

Completa los campos:

| Campo | Valor |
|-------|-------|
| **Name** | `servicio-bi` (o el nombre que prefieras) |
| **Region** | `Oregon (US West)` o el más cercano |
| **Branch** | `main` |
| **Root Directory** | *(dejar vacío)* |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |

### 4. Variables de Entorno

Click en **"Advanced"** y luego **"Add Environment Variable"**

Agrega las siguientes variables:

#### PostgreSQL (Supabase)
```
PG_DATABASE = postgres
PG_USER = postgres.xxxxxxxxx
PG_PASSWORD = tu_password
PG_HOST = aws-1-us-east-2.pooler.supabase.com
PG_PORT = 6543
PG_SSLMODE = require
```

#### MongoDB Atlas
```
MONGO_URI = mongodb+srv://user:password@cluster.mongodb.net/agencia_viajes
MONGO_DATABASE = agencia_viajes
```

**⚠️ IMPORTANTE:** Reemplaza con tus credenciales reales de:
- Supabase (PostgreSQL)
- MongoDB Atlas

### 5. Desplegar

1. Click en **"Create Web Service"**
2. Render comenzará a:
   - ✅ Clonar tu repositorio
   - ✅ Instalar Python
   - ✅ Instalar dependencias
   - ✅ Iniciar tu aplicación

3. Espera 3-5 minutos mientras se despliega

### 6. Verificar Despliegue

Una vez desplegado, verás:
- ✅ Estado: **"Live"** (verde)
- ✅ URL: `https://servicio-bi-xxxx.onrender.com`

#### Probar la API:
```bash
# Health check
https://servicio-bi-xxxx.onrender.com/health

# Documentación interactiva
https://servicio-bi-xxxx.onrender.com/docs

# Dashboard
https://servicio-bi-xxxx.onrender.com/dashboard/resumen
```

---

## 🔧 Configuraciones Adicionales

### Permitir conexión desde Render a MongoDB Atlas

1. Ve a MongoDB Atlas → Network Access
2. Click **"Add IP Address"**
3. Agrega: **`0.0.0.0/0`** (permitir todas las IPs)
   - O la IP específica de Render si la conoces
4. Click **"Confirm"**

### Verificar PostgreSQL (Supabase)

1. Supabase ya permite conexiones desde cualquier IP
2. Asegúrate de usar: `PG_SSLMODE=require`
3. Usa el **Pooler connection** (puerto 6543), no el directo

---

## 📊 Monitoreo

### Ver Logs en Render

1. Ve a tu servicio en Render Dashboard
2. Click en **"Logs"** (menú lateral)
3. Deberías ver:
   ```
   🚀 Iniciando aplicación...
   ✅ Conectado a MongoDB para sincronización en tiempo real
   👀 Iniciando monitoreo de cambios...
   🔄 Monitoreo activo. Esperando cambios en MongoDB...
   ```

### Métricas

- **CPU Usage**: < 50% normal
- **Memory**: ~200-300 MB normal
- **Response Time**: < 2s promedio

---

## ⚠️ Troubleshooting

### Error: "Build failed"
- ✅ Verifica que `requirements.txt` esté correcto
- ✅ Asegúrate que el Build Command sea: `pip install -r requirements.txt`

### Error: "Application failed to respond"
- ✅ Verifica que las variables de entorno estén correctas
- ✅ Revisa los logs para ver el error específico

### Error: "Can't connect to MongoDB"
- ✅ Verifica la IP whitelist en MongoDB Atlas
- ✅ Confirma que `MONGO_URI` sea correcto

### Error: "Can't connect to PostgreSQL"
- ✅ Usa `PG_SSLMODE=require`
- ✅ Usa el Pooler connection (puerto 6543)
- ✅ Verifica credenciales de Supabase

---

## 🎯 Checklist Post-Despliegue

- [ ] Servicio en estado "Live"
- [ ] `/health` responde correctamente
- [ ] `/sync/status` muestra sincronización activa
- [ ] `/dashboard/resumen` retorna datos
- [ ] `/docs` carga la documentación
- [ ] Logs no muestran errores
- [ ] MongoDB conectado
- [ ] PostgreSQL conectado

---

## 🔄 Actualizar el Servicio

Cada vez que hagas push a GitHub:
1. Render detectará los cambios automáticamente
2. Reconstruirá y redespl egará
3. **Auto-deploy** está habilitado por defecto

Para deshabilitarlo:
- Settings → Auto-Deploy → Disable

---

## 💰 Plan Free de Render

**Limitaciones:**
- ✅ 750 horas/mes gratis (suficiente para 1 servicio 24/7)
- ⚠️ Se duerme después de 15 min de inactividad
- ⚠️ Tarda ~30 seg en despertar al recibir request
- ✅ Dominio HTTPS gratis
- ✅ Auto-deploy desde GitHub

**Solución para mantenerlo despierto:**
- Usar un servicio de "ping" (UptimeRobot, cron-job.org)
- Hacer request cada 10 minutos

---

## 🌐 URL Final

Tu servicio estará disponible en:
```
https://tu-servicio.onrender.com
```

**Comparte esta URL con:**
- Tu compañero (para integrar con frontend)
- Tu profesor (para revisión)
- Documentación (README.md)

---

## 📝 Próximos Pasos

1. ✅ Desplegar en Render
2. ✅ Probar todos los endpoints
3. ✅ Compartir URL con tu compañero
4. ✅ Integrar con frontend
5. ✅ Preparar demo para presentación

---

**¿Necesitas ayuda?**
- Render Docs: https://render.com/docs
- Comunidad: https://community.render.com

**Creado por:** Estudiante SW2
**Fecha:** Noviembre 2025
