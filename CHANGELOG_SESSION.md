# 🚀 Resumen de Cambios - Servicio BI

## 📊 Estado General

- **Servicio**: Desplegado y funcionando en Render ([https://sw2-servicio-bi.onrender.com](https://sw2-servicio-bi.onrender.com))
- **Branch**: `main`
- **Último commit**: `55b9c6f` - docs(sql): add comprehensive README for RLS setup

---

## ✅ Cambios Implementados (Sesión Actual)

### 1. **Pool Centralizado de PostgreSQL** ✨ [CRÍTICO]

**Problema resuelto:** Error intermitente `"Attempted to check out a connection from closed connection pool"` durante shutdown/restart.

**Solución:**
- Nuevo módulo de pool en `app/db.py`:
  - `init_pool(min_size, max_size)` - Inicializa pool global en startup
  - `close_pool()` - Cierra pool ordenadamente en shutdown
  - `get_conn()` - Retorna conexión del pool si está disponible, fallback a conexión directa
- Integración en `app/main.py`:
  - Pool se inicializa **antes** de arrancar el realtime worker
  - Pool se cierra **después** de detener el realtime worker
- `app/etl.py` actualizado para usar el pool cuando esté disponible

**Commit:** `2923724` - feat(db): add global psycopg pool init/close and use pool from ETL

**Impacto esperado:**
- ✅ Reducción drástica de errores "closed connection pool"
- ✅ Mejor gestión de recursos y conexiones
- ✅ Shutdown ordenado sin carreras entre worker y conexiones

---

### 2. **Row Level Security (RLS) - Scripts y Documentación** 🔐

**Problema resuelto:** Supabase linter reportaba 7 tablas sin RLS habilitado.

**Solución:**
- **Script SQL:** `sql/enable_rls_and_policies.sql`
  - Habilita RLS en todas las tablas críticas
  - Crea políticas permisivas para el rol `etl_role`
  - Incluye checks `IF NOT EXISTS` para idempotencia
  
- **Documentación completa:** `sql/README.md`
  - Instrucciones paso a paso para ejecutar en Supabase SQL Editor
  - Sección de troubleshooting con soluciones a errores comunes
  - Comandos de verificación post-ejecución
  - Alternativas para psql (línea de comandos)
  - Ejemplos de políticas más restrictivas

**Commits:**
- `ec48176` - chore(sql): agregar script para habilitar RLS y policies para rol etl_role
- `55b9c6f` - docs(sql): add comprehensive README for RLS setup with troubleshooting

**Acción requerida del usuario:**
👉 **Ejecutar el script manualmente** en Supabase SQL Editor siguiendo `sql/README.md`

**Tablas protegidas:**
- `public.agentes`
- `public.clientes`
- `public.detalle_venta`
- `public.pagos`
- `public.paquetes_turisticos`
- `public.servicios`
- `public.ventas`

---

## 🔧 Cambios Previos (Contexto)

### Mitigaciones de Shutdown
- **Commit:** `1ef11cc` - fix(realtime): avoid closing mongo client before worker join
- **Commit:** `45a9e1d` - fix(realtime): graceful stop for change-stream worker

### Reintentos/Backoff en ETL
- **Commit:** `5b3afe9` - fix(etl): add retries/backoff for PG connection and sync_data

---

## 🎯 Próximos Pasos Recomendados

### Alta Prioridad

1. **Ejecutar script RLS en Supabase** 🔐
   - Abrir `sql/README.md` y seguir las instrucciones
   - Verificar que las políticas se crearon correctamente
   - Probar inserción con el rol ETL

2. **Monitorear logs de Render** 📊
   - Verificar que el pool se inicializa: `"✅ Pool de PostgreSQL inicializado"`
   - Confirmar reducción de errores "closed connection pool"
   - Observar tiempos de startup/shutdown

3. **Verificar variables de entorno en Render** ⚙️
   - `MONGO_URI` (marcar como secret)
   - `PG_*` (database, user, password, host, port)
   - `BI_AUTH_TOKEN` (si está implementado)

### Media Prioridad

4. **Endpoint `/sync/once`** 🔄
   - POST endpoint protegido por token
   - Invoca `sync_data()` manualmente
   - Útil para debugging y despliegues

5. **Prueba E2E completa** ✅
   - Insertar documento en MongoDB (colección `clientes`)
   - Verificar que aparece en PostgreSQL
   - Validar change-stream y sincronización automática

### Baja Prioridad

6. **Aumentar instrumentación** 📝
   - Incrementar timeout de join a 30s
   - Logs adicionales en secciones críticas

7. **Validación de BI_AUTH_TOKEN** 🔑
   - Middleware para validar token en endpoints críticos
   - Restricción de acceso backend→backend

---

## 📈 Métricas de Éxito

### ✅ Completado
- [x] Servicio desplegado y respondiendo en Render
- [x] Endpoints `/health`, `/sync/status`, `/dashboard/resumen`, KPIs funcionando
- [x] Change-stream activo y sincronización en tiempo real
- [x] Pool centralizado implementado
- [x] Scripts RLS generados y documentados

### 🔄 En Progreso
- [ ] Ejecutar script RLS en Supabase (acción manual del usuario)
- [ ] Monitorear reducción de errores "closed pool" post-deploy

### ⏳ Pendiente
- [ ] Endpoint `/sync/once`
- [ ] Prueba E2E inserción Mongo→Postgres
- [ ] Validación completa de BI_AUTH_TOKEN

---

## 🛠️ Comandos Útiles

### Local

```powershell
# Verificar estado del repo
git status
git log --oneline -n 5

# Levantar stack local con Docker Compose
docker-compose up -d

# Ver logs del servicio
docker-compose logs -f servicio-bi
```

### Render (vía Web UI)

1. Ir a [Render Dashboard](https://dashboard.render.com)
2. Seleccionar servicio `sw2-servicio-bi`
3. Pestaña **Logs** → **Live Logs**
4. Buscar:
   - `"✅ Pool de PostgreSQL inicializado"`
   - `"✅ Sincronización en tiempo real activada"`
   - `"🔄 Iniciando sincronización de datos..."`

### Probar Endpoints

```powershell
# Health check
Invoke-RestMethod https://sw2-servicio-bi.onrender.com/health

# Estado de sincronización
Invoke-RestMethod https://sw2-servicio-bi.onrender.com/sync/status

# Dashboard (con parámetros opcionales)
Invoke-RestMethod "https://sw2-servicio-bi.onrender.com/dashboard/resumen?fecha_inicio=2024-01-01&fecha_fin=2024-12-31"

# Margen bruto
Invoke-RestMethod https://sw2-servicio-bi.onrender.com/kpi/margen-bruto
```

---

## 📚 Recursos

- **Repositorio:** [github.com/ainturias/sw2-servicio-bi](https://github.com/ainturias/sw2-servicio-bi)
- **Servicio en Render:** [sw2-servicio-bi.onrender.com](https://sw2-servicio-bi.onrender.com)
- **Documentación RLS:** `sql/README.md`
- **API Docs (Swagger):** [sw2-servicio-bi.onrender.com/docs](https://sw2-servicio-bi.onrender.com/docs)

---

## 💡 Notas Importantes

1. **Pool de Postgres:** Requiere `psycopg[binary]` instalado (ya está en `requirements.txt`). Si hay problemas, verificar que la versión es `psycopg>=3.0`.

2. **RLS:** El script usa políticas permisivas (`USING (true)`). Para producción, considera políticas más restrictivas basadas en tenant_id o limitando operaciones específicas.

3. **Service Role:** Si el ETL usa `service_role` de Supabase, RLS no es necesario (service_role ignora RLS automáticamente).

4. **Monitoreo continuo:** El error "closed connection pool" debería desaparecer o reducirse significativamente. Si persiste, considera aumentar `max_size` del pool o revisar tiempos de timeout.

---

**Última actualización:** 9 de noviembre de 2025  
**Autor:** GitHub Copilot (asistente IA)
