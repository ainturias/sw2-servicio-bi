# Habilitar Row Level Security (RLS) en Supabase

Este directorio contiene el script SQL necesario para habilitar RLS y crear políticas de acceso para el rol ETL.

## 📋 Requisitos previos

- Acceso al proyecto Supabase con privilegios de administrador/superuser
- Conocer el usuario/role que usa tu proceso ETL para conectarse a Postgres

## 🚀 Instrucciones de ejecución

### Opción 1: SQL Editor de Supabase (recomendado)

1. **Abrir SQL Editor**
   - Ir a tu proyecto en [Supabase Dashboard](https://app.supabase.com)
   - En el menú lateral, hacer clic en **SQL Editor**

2. **Crear nueva query**
   - Clic en **New Query**

3. **Copiar y pegar el script**
   - Abrir el archivo `enable_rls_and_policies.sql` en tu editor local
   - Copiar todo el contenido
   - Pegarlo en el editor SQL de Supabase

4. **Ejecutar el script**
   - Clic en el botón **Run** o presionar `Ctrl+Enter` (Windows) / `Cmd+Enter` (Mac)
   - Esperar a que se complete la ejecución (debería tomar unos segundos)

5. **Verificar que las políticas se crearon**
   - Ejecutar esta query en el SQL Editor:
   ```sql
   SELECT polname, polrelid::regclass 
   FROM pg_policy 
   WHERE polname LIKE '%_etl_full_access%'
   ORDER BY polrelid::regclass;
   ```
   - Deberías ver 7 filas (una por cada tabla: agentes, clientes, detalle_venta, pagos, paquetes_turisticos, servicios, ventas)

### Opción 2: psql (línea de comandos)

Si prefieres usar la línea de comandos:

```bash
# Reemplazar los valores entre < > con tus credenciales reales
psql "postgresql://<SUPERUSER>@<HOST>:5432/<DATABASE>?sslmode=require" -f sql/enable_rls_and_policies.sql
```

**Ejemplo:**
```bash
psql "postgresql://postgres.abcd1234@aws-1-us-east-2.pooler.supabase.com:5432/postgres?sslmode=require" -f sql/enable_rls_and_policies.sql
```

## 🔐 Qué hace el script

El script realiza las siguientes acciones para cada tabla:

1. **Habilita RLS** en la tabla usando `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
2. **Crea una política permisiva** llamada `<tabla>_etl_full_access` que:
   - Permite operaciones: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
   - Para el rol: `etl_role`
   - Condición: `USING (true) WITH CHECK (true)` (sin restricciones)

### Tablas protegidas

- `public.agentes`
- `public.clientes`
- `public.detalle_venta`
- `public.pagos`
- `public.paquetes_turisticos`
- `public.servicios`
- `public.ventas`

## ⚙️ Configuración del rol ETL

### Si el rol `etl_role` no existe

El script incluye comentarios sobre cómo crear el rol. Descomenta y ejecuta estas líneas antes del resto del script:

```sql
-- Crear el rol si no existe
CREATE ROLE "etl_role" NOINHERIT;

-- Otorgar el rol al usuario que usa el ETL (reemplazar <TU_USUARIO>)
GRANT "etl_role" TO "<TU_USUARIO>";
```

**Nota:** Reemplaza `<TU_USUARIO>` con el usuario real que aparece en tu variable `PG_USER` o connection string.

### Si tu ETL usa service_role

Si tu proceso ETL se conecta usando la `service_role` de Supabase, **NO necesitas ejecutar este script**. La service_role ignora RLS automáticamente.

Para verificar qué usuario/role usas:
1. Revisar la variable de entorno `PG_USER` en Render
2. O ejecutar esta query en Supabase:
   ```sql
   SELECT current_user;
   ```

## 🔍 Verificación post-ejecución

### 1. Verificar que RLS está habilitado

```sql
SELECT 
    schemaname, 
    tablename, 
    rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN ('agentes', 'clientes', 'detalle_venta', 'pagos', 'paquetes_turisticos', 'servicios', 'ventas');
```

Todas las tablas deberían mostrar `rowsecurity = true`.

### 2. Verificar las políticas

```sql
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
    AND policyname LIKE '%_etl_full_access%'
ORDER BY tablename;
```

### 3. Probar inserción con el rol ETL

Si tienes configurado el rol correctamente:

```sql
SET ROLE etl_role;
INSERT INTO clientes (origen_id, nombre, email, fecha_registro) 
VALUES ('test_rls_001', 'Test RLS', 'test@example.com', NOW());

-- Verificar
SELECT * FROM clientes WHERE origen_id = 'test_rls_001';

-- Limpiar
DELETE FROM clientes WHERE origen_id = 'test_rls_001';
RESET ROLE;
```

## ⚠️ Troubleshooting

### Error: "permission denied to create policy"

**Causa:** No tienes privilegios de superuser.

**Solución:** 
- Ejecuta el script desde el SQL Editor de Supabase (que usa credenciales admin)
- O conecta con un usuario que tenga privilegios `SUPERUSER` o `BYPASSRLS`

### Error: "role 'etl_role' does not exist"

**Causa:** El rol no ha sido creado.

**Solución:**
1. Crear el rol ejecutando:
   ```sql
   CREATE ROLE "etl_role" NOINHERIT;
   GRANT "etl_role" TO "postgres";  -- O tu usuario
   ```
2. Ejecutar de nuevo el script completo

### El ETL no puede insertar datos después de habilitar RLS

**Causa:** El usuario del ETL no tiene el rol `etl_role` asignado.

**Solución:**
1. Verificar el usuario actual:
   ```sql
   SELECT current_user;
   ```
2. Otorgar el rol:
   ```sql
   GRANT "etl_role" TO "<usuario_etl>";
   ```

### Quiero políticas más restrictivas

El script actual usa `USING (true) WITH CHECK (true)`, que es permisivo para facilitar el despliegue inicial.

Para políticas más seguras (por ejemplo, filtrar por tenant_id o limitar operaciones):

**Ejemplo - Solo INSERT/UPDATE/DELETE (sin SELECT):**
```sql
CREATE POLICY clientes_etl_write ON public.clientes 
FOR INSERT TO "etl_role" 
WITH CHECK (true);

CREATE POLICY clientes_etl_update ON public.clientes 
FOR UPDATE TO "etl_role" 
USING (true) WITH CHECK (true);
```

## 📚 Referencias

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL Policies](https://www.postgresql.org/docs/current/sql-createpolicy.html)
- [PostgreSQL Roles](https://www.postgresql.org/docs/current/sql-createrole.html)

## 🆘 Soporte

Si encuentras problemas al ejecutar el script:
1. Revisar los logs del proceso ETL en Render
2. Verificar que las variables `PG_*` están correctamente configuradas
3. Consultar la sección de Troubleshooting arriba
