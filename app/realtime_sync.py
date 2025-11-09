"""
Módulo para sincronización en tiempo real desde MongoDB a PostgreSQL
Usa Change Streams de MongoDB para detectar cambios y actualizar PostgreSQL automáticamente
"""
import os
import logging
from pymongo import MongoClient
from threading import Thread
import time
from app.etl import sync_data

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealtimeSync:
    """Clase para manejar la sincronización en tiempo real"""
    
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI")
        self.mongo_db = os.getenv("MONGO_DATABASE", "agencia_viajes")
        self.client = None
        self.is_running = False
        self._thread = None
        
    def connect(self):
        """Conectar a MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            # Verificar conexión
            self.client.admin.command('ping')
            logger.info("✅ Conectado a MongoDB para sincronización en tiempo real")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB: {e}")
            return False
    
    def watch_changes(self):
        """
        Observar cambios en MongoDB usando Change Streams
        Cuando hay un cambio, ejecuta la sincronización
        """
        if not self.client:
            logger.error("❌ No hay conexión a MongoDB")
            return
        
        db = self.client[self.mongo_db]
        logger.info(f"👀 Iniciando monitoreo de cambios en base de datos: {self.mongo_db}")
        
        # Colecciones a monitorear
        collections_to_watch = [
            'clientes', 
            'agentes', 
            'servicios', 
            'paquetes_turisticos', 
            'ventas', 
            'detalle_venta'
        ]
        
        try:
            # Crear un change stream para toda la base de datos
            logger.info("🔄 Intentando crear change stream para monitoreo de DB")
            with db.watch() as stream:
                logger.info("🔄 Monitoreo activo. Esperando cambios en MongoDB...")
                self.is_running = True

                for change in stream:
                    # Permitir salida rápida si alguien pidió detener
                    if not self.is_running:
                        logger.info("🔹 Detención solicitada, saliendo del bucle de change stream")
                        break

                    # Obtener información del cambio
                    operation = change.get('operationType')
                    ns = change.get('ns', {})
                    collection = ns.get('coll')

                    # Solo procesar cambios en las colecciones que nos interesan
                    if collection in collections_to_watch:
                        logger.info(f"🔔 Cambio detectado: {operation} en {collection}")

                        # Ejecutar sincronización
                        try:
                            logger.info("🔄 Iniciando sincronización de datos...")
                            sync_data()
                            logger.info("✅ Sincronización completada exitosamente")
                        except Exception as e:
                            logger.error(f"❌ Error durante la sincronización: {e}")

        except Exception as e:
            logger.error(f"❌ Error en el monitoreo de cambios: {e}")
            self.is_running = False
    
    def start(self):
        """Iniciar el monitoreo en un hilo separado"""
        if not self.connect():
            logger.error("❌ No se pudo iniciar la sincronización en tiempo real")
            return False

        # Iniciar el monitoreo en un hilo separado y guardar referencia
        self._thread = Thread(target=self.watch_changes, daemon=True)
        self._thread.start()
        logger.info("🚀 Sincronización en tiempo real iniciada")
        return True
    
    def stop(self):
        """Detener el monitoreo"""
        logger.info("⏹️ Solicitud de detención de sincronización en tiempo real recibida")
        # Señalar al hilo que debe terminar
        self.is_running = False

        # Cerrar cliente si existe (esto ayuda a que db.watch() termine)
        if self.client:
            try:
                self.client.close()
                logger.info("🔌 Cliente MongoDB cerrado")
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando cliente MongoDB: {e}")

        # Intentar unir (join) el hilo hasta un timeout para evitar workers huérfanos
        if self._thread and self._thread.is_alive():
            logger.info("🔁 Esperando que el hilo de monitoreo termine...")
            try:
                self._thread.join(timeout=5)
                if self._thread.is_alive():
                    logger.warning("⚠️ El hilo de monitoreo no terminó tras el timeout")
                else:
                    logger.info("✅ Hilo de monitoreo finalizado")
            except Exception as e:
                logger.warning(f"⚠️ Error al unir hilo de monitoreo: {e}")

        logger.info("⏹️ Sincronización en tiempo real detenida")


# Instancia global del sincronizador
realtime_sync = RealtimeSync()


def start_realtime_sync():
    """Función helper para iniciar la sincronización"""
    return realtime_sync.start()


def stop_realtime_sync():
    """Función helper para detener la sincronización"""
    realtime_sync.stop()
