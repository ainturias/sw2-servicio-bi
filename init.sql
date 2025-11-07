-- Script de inicialización de la base de datos para el servicio de Business Intelligence
-- Modelo operacional simplificado que soporta todos los KPIs requeridos

-- ============================================================================
-- TABLAS PRINCIPALES
-- ============================================================================

-- Tabla de clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    origen_id VARCHAR(255) UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de agentes
CREATE TABLE IF NOT EXISTS agentes (
    id SERIAL PRIMARY KEY,
    origen_id VARCHAR(255) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    telefono VARCHAR(20)
);

-- Tabla de servicios
CREATE TABLE IF NOT EXISTS servicios (
    id SERIAL PRIMARY KEY,
    origen_id VARCHAR(255) UNIQUE NOT NULL,
    destino_ciudad VARCHAR(200),
    destino_pais VARCHAR(100),
    precio_costo DECIMAL(10, 2) DEFAULT 0
);

-- Tabla de paquetes turísticos
CREATE TABLE IF NOT EXISTS paquetes_turisticos (
    id SERIAL PRIMARY KEY,
    origen_id VARCHAR(255) UNIQUE NOT NULL,
    destino_principal VARCHAR(200),
    precio_total_venta DECIMAL(10, 2) DEFAULT 0
);

-- Tabla de ventas
CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    origen_id VARCHAR(255) UNIQUE,
    cliente_id INTEGER REFERENCES clientes(id),
    agente_id INTEGER REFERENCES agentes(id),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' 
        CHECK (estado IN ('pendiente', 'confirmada', 'cancelada', 'finalizada', 'emitida')),
    monto DECIMAL(10, 2) NOT NULL,
    fecha_venta DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    puntuacion_satisfaccion INTEGER CHECK (puntuacion_satisfaccion >= 1 AND puntuacion_satisfaccion <= 5)
);

-- Tabla de detalle_venta
CREATE TABLE IF NOT EXISTS detalle_venta (
    id SERIAL PRIMARY KEY,
    origen_id VARCHAR(255) UNIQUE,
    venta_id INTEGER REFERENCES ventas(id) ON DELETE CASCADE,
    servicio_id INTEGER REFERENCES servicios(id),
    paquete_id INTEGER REFERENCES paquetes_turisticos(id),
    descripcion VARCHAR(200),
    cantidad INTEGER DEFAULT 1 NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL
);

-- Tabla de pagos (opcional, mencionada en requerimientos)
CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER REFERENCES ventas(id) ON DELETE CASCADE,
    monto DECIMAL(10, 2) NOT NULL,
    fecha_pago TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metodo_pago VARCHAR(50)
);

-- ============================================================================
-- ÍNDICES PARA OPTIMIZAR CONSULTAS DE ENDPOINTS KPI
-- ============================================================================

-- Índice en fecha_venta: Acelera filtros por rango de fechas en todos los endpoints KPI
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas (fecha_venta);

-- Índice en estado: Optimiza filtros WHERE estado = 'confirmada'/'cancelada'
CREATE INDEX IF NOT EXISTS idx_ventas_estado ON ventas (estado);

-- Índice compuesto para consultas que filtran por fecha y estado
CREATE INDEX IF NOT EXISTS idx_ventas_fecha_estado ON ventas (fecha_venta, estado);

-- Índice en venta_id: Acelera JOINs entre ventas y detalle_venta
CREATE INDEX IF NOT EXISTS idx_detalle_venta_venta ON detalle_venta (venta_id);

-- Índice en servicio_id: Optimiza JOINs con servicios
CREATE INDEX IF NOT EXISTS idx_detalle_venta_servicio ON detalle_venta (servicio_id);

-- Índice en paquete_id: Optimiza JOINs con paquetes_turisticos
CREATE INDEX IF NOT EXISTS idx_detalle_venta_paquete ON detalle_venta (paquete_id);

-- Índice compuesto en destino_ciudad y destino_pais: Optimiza agrupaciones por destino
CREATE INDEX IF NOT EXISTS idx_servicios_destino ON servicios (destino_ciudad, destino_pais);

-- Índice en destino_principal: Optimiza consultas de paquetes turísticos
CREATE INDEX IF NOT EXISTS idx_paquetes_destino ON paquetes_turisticos (destino_principal);

-- Índice en origen_id para tablas principales (acelera UPSERTs del ETL)
CREATE INDEX IF NOT EXISTS idx_clientes_origen ON clientes (origen_id);
CREATE INDEX IF NOT EXISTS idx_agentes_origen ON agentes (origen_id);
CREATE INDEX IF NOT EXISTS idx_ventas_origen ON ventas (origen_id);
CREATE INDEX IF NOT EXISTS idx_detalle_venta_origen ON detalle_venta (origen_id);

-- ============================================================================
-- DATOS DE PRUEBA (solo para desarrollo local)
-- ============================================================================

-- Insertar clientes de ejemplo
INSERT INTO clientes (origen_id, nombre, email, telefono) VALUES
    ('cliente_001', 'Juan Pérez', 'juan.perez@email.com', '555-0101'),
    ('cliente_002', 'María García', 'maria.garcia@email.com', '555-0102'),
    ('cliente_003', 'Carlos López', 'carlos.lopez@email.com', '555-0103'),
    ('cliente_004', 'Ana Martínez', 'ana.martinez@email.com', '555-0104'),
    ('cliente_005', 'Pedro Sánchez', 'pedro.sanchez@email.com', '555-0105')
ON CONFLICT (email) DO NOTHING;

-- Insertar agentes de ejemplo
INSERT INTO agentes (origen_id, nombre, email, telefono) VALUES
    ('agente_001', 'Laura Rodríguez', 'laura.rodriguez@agencia.com', '555-1001'),
    ('agente_002', 'Roberto Silva', 'roberto.silva@agencia.com', '555-1002'),
    ('agente_003', 'Carmen Vega', 'carmen.vega@agencia.com', '555-1003')
ON CONFLICT (origen_id) DO NOTHING;

-- Insertar servicios de ejemplo
INSERT INTO servicios (origen_id, destino_ciudad, destino_pais, precio_costo) VALUES
    ('servicio_001', 'París', 'Francia', 1200.00),
    ('servicio_002', 'Roma', 'Italia', 1100.00),
    ('servicio_003', 'Londres', 'Reino Unido', 900.00),
    ('servicio_004', 'Madrid', 'España', 800.00),
    ('servicio_005', 'Barcelona', 'España', 750.00),
    ('servicio_006', 'Nueva York', 'Estados Unidos', 1800.00),
    ('servicio_007', 'Amsterdam', 'Países Bajos', 700.00),
    ('servicio_008', 'Tokio', 'Japón', 1500.00)
ON CONFLICT (origen_id) DO NOTHING;

-- Insertar paquetes turísticos de ejemplo
INSERT INTO paquetes_turisticos (origen_id, destino_principal, precio_total_venta) VALUES
    ('paquete_001', 'Dubai', 3000.00),
    ('paquete_002', 'Bali', 2500.00),
    ('paquete_003', 'Maldivas', 2800.00)
ON CONFLICT (origen_id) DO NOTHING;

-- Insertar ventas de ejemplo
INSERT INTO ventas (origen_id, cliente_id, agente_id, monto, estado, fecha_venta, puntuacion_satisfaccion) VALUES
    ('venta_001', 1, 1, 1500.00, 'confirmada', '2024-01-15', 5),
    ('venta_002', 2, 1, 2300.50, 'confirmada', '2024-01-16', 4),
    ('venta_003', 3, 2, 850.75, 'confirmada', '2024-01-17', 5),
    ('venta_004', 4, 2, 1200.00, 'confirmada', '2024-01-18', 4),
    ('venta_005', 5, 3, 950.25, 'confirmada', '2024-01-19', 5),
    ('venta_006', 1, 1, 2000.00, 'confirmada', '2024-01-20', 4),
    ('venta_007', 2, 2, 750.00, 'confirmada', '2024-01-21', 3),
    ('venta_008', 3, 3, 1800.00, 'confirmada', '2024-01-22', 5),
    ('venta_009', 4, 1, 500.00, 'cancelada', '2024-01-23', NULL),
    ('venta_010', 5, 2, 1200.00, 'cancelada', '2024-01-24', NULL),
    ('venta_011', 1, 3, 3000.00, 'finalizada', '2024-01-25', 5),
    ('venta_012', 2, 1, 450.00, 'cancelada', '2024-01-26', NULL)
ON CONFLICT (origen_id) DO NOTHING;

-- Insertar detalles de venta de ejemplo
INSERT INTO detalle_venta (origen_id, venta_id, servicio_id, paquete_id, descripcion, cantidad, precio_unitario, subtotal) VALUES
    ('detalle_001', 1, 1, NULL, 'Viaje a París', 1, 1500.00, 1500.00),
    ('detalle_002', 2, 2, NULL, 'Viaje a Roma', 2, 1150.25, 2300.50),
    ('detalle_003', 3, 3, NULL, 'Tour Londres', 1, 850.75, 850.75),
    ('detalle_004', 4, 4, NULL, 'Viaje a Madrid', 1, 1200.00, 1200.00),
    ('detalle_005', 5, 5, NULL, 'Tour Barcelona', 1, 950.25, 950.25),
    ('detalle_006', 6, 6, NULL, 'Viaje a Nueva York', 1, 2000.00, 2000.00),
    ('detalle_007', 7, 7, NULL, 'Tour Amsterdam', 1, 750.00, 750.00),
    ('detalle_008', 8, 8, NULL, 'Viaje a Tokio', 1, 1800.00, 1800.00),
    ('detalle_009', 9, 1, NULL, 'Viaje a París', 1, 500.00, 500.00),
    ('detalle_010', 10, 2, NULL, 'Tour Praga', 1, 1200.00, 1200.00),
    ('detalle_011', 11, NULL, 1, 'Paquete Dubai', 1, 3000.00, 3000.00),
    ('detalle_012', 12, 7, NULL, 'Tour Viena', 1, 450.00, 450.00)
ON CONFLICT (origen_id) DO NOTHING;
