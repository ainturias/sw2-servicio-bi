-- Script para habilitar Row Level Security (RLS) y crear políticas para el rol ETL
-- USO: revisar y ejecutar en el SQL Editor de Supabase o mediante psql con un superuser.
-- Este script crea políticas permisivas (USING true) para el rol 'etl_role'.

-- Si prefieres otro nombre de rol, reemplaza 'etl_role' por el nombre deseado.
-- Si tu ETL usa la service_role de Supabase no es necesario activar estas policies.

-- 1) (opcional) Crear el rol ETL manualmente si no existe:
--    CREATE ROLE "etl_role" NOINHERIT;
--    GRANT "etl_role" TO "postgres"; -- ajustar según usuario

-- Lista de tablas a proteger (ajusta si tu esquema difiere)
-- agentes, paquetes_turisticos, clientes, ventas, detalle_venta, servicios, pagos

-- NOTE: ejecutar cada bloque DO $$ ... $$; requiere privilegios de superuser

-- Tabla: agentes
ALTER TABLE IF EXISTS public.agentes ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'agentes_etl_full_access' AND polrelid = 'public.agentes'::regclass) THEN
    EXECUTE 'CREATE POLICY agentes_etl_full_access ON public.agentes FOR ALL TO "etl_role" USING (true) WITH CHECK (true);';
  END IF;
END$$;

-- Tabla: paquetes_turisticos
ALTER TABLE IF EXISTS public.paquetes_turisticos ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'paquetes_turisticos_etl_full_access' AND polrelid = 'public.paquetes_turisticos'::regclass) THEN
    EXECUTE 'CREATE POLICY paquetes_turisticos_etl_full_access ON public.paquetes_turisticos FOR ALL TO "etl_role" USING (true) WITH CHECK (true);';
  END IF;
END$$;

-- Tabla: clientes
ALTER TABLE IF EXISTS public.clientes ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'clientes_etl_full_access' AND polrelid = 'public.clientes'::regclass) THEN
    EXECUTE 'CREATE POLICY clientes_etl_full_access ON public.clientes FOR ALL TO "etl_role" USING (true) WITH CHECK (true);';
  END IF;
END$$;

-- Tabla: ventas
ALTER TABLE IF EXISTS public.ventas ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'ventas_etl_full_access' AND polrelid = 'public.ventas'::regclass) THEN
    EXECUTE 'CREATE POLICY ventas_etl_full_access ON public.ventas FOR ALL TO "etl_role" USING (true) WITH CHECK (true);';
  END IF;
END$$;

-- Tabla: detalle_venta
ALTER TABLE IF EXISTS public.detalle_venta ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'detalle_venta_etl_full_access' AND polrelid = 'public.detalle_venta'::regclass) THEN
    EXECUTE 'CREATE POLICY detalle_venta_etl_full_access ON public.detalle_venta FOR ALL TO "etl_role" USING (true) WITH CHECK (true);';
  END IF;
END$$;

-- Tabla: servicios
ALTER TABLE IF EXISTS public.servicios ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'servicios_etl_full_access' AND polrelid = 'public.servicios'::regclass) THEN
    EXECUTE 'CREATE POLICY servicios_etl_full_access ON public.servicios FOR ALL TO "etl_role" USING (true) WITH CHECK (true);';
  END IF;
END$$;

-- Tabla: pagos
ALTER TABLE IF EXISTS public.pagos ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'pagos_etl_full_access' AND polrelid = 'public.pagos'::regclass) THEN
    EXECUTE 'CREATE POLICY pagos_etl_full_access ON public.pagos FOR ALL TO "etl_role" USING (true) WITH CHECK (true);';
  END IF;
END$$;

-- Verificación rápida (opcional):
-- SELECT polname, polrelid::regclass FROM pg_policy WHERE polname LIKE '%_etl_full_access%';

-- FIN
