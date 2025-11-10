# 🐳 Guía para Docker y Kubernetes

## 📋 Prerequisitos
- Docker Desktop instalado
- Cuenta en Docker Hub (https://hub.docker.com)

---

## 🏗️ Construir la imagen Docker

### 1. Login en Docker Hub
```bash
docker login
# Ingresa tu usuario y contraseña de Docker Hub
```

### 2. Construir la imagen
```bash
# Reemplaza 'tuusuario' con tu nombre de usuario de Docker Hub
docker build -t tuusuario/servicio-bi:latest .
```

### 3. Probar la imagen localmente
```bash
# Ejecutar el contenedor con variables de entorno
docker run -p 8000:8000 \
  -e MONGO_URI="tu_mongo_uri" \
  -e MONGO_DATABASE="agencia_viajes" \
  -e POSTGRES_URI="tu_postgres_uri" \
  tuusuario/servicio-bi:latest

# Probar: http://localhost:8000/health
```

### 4. Publicar en Docker Hub
```bash
docker push tuusuario/servicio-bi:latest
```

---

## 🚀 Para tu compañero con Kubernetes

### Archivo de deployment para Kubernetes (`k8s-deployment.yaml`)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: servicio-bi-config
data:
  MONGO_DATABASE: "agencia_viajes"
  # Agregar otras variables NO sensibles aquí

---
apiVersion: v1
kind: Secret
metadata:
  name: servicio-bi-secrets
type: Opaque
stringData:
  MONGO_URI: "mongodb+srv://usuario:password@cluster.mongodb.net"
  POSTGRES_URI: "postgresql://usuario:password@host:5432/database"
  # Agregar credenciales aquí

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: servicio-bi
  labels:
    app: servicio-bi
spec:
  replicas: 2
  selector:
    matchLabels:
      app: servicio-bi
  template:
    metadata:
      labels:
        app: servicio-bi
    spec:
      containers:
      - name: servicio-bi
        image: tuusuario/servicio-bi:latest  # ← Cambiar por tu imagen
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: servicio-bi-config
        - secretRef:
            name: servicio-bi-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: servicio-bi-service
spec:
  selector:
    app: servicio-bi
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer  # O ClusterIP si solo se usa internamente
```

### Tu compañero debe ejecutar:

```bash
# Aplicar el deployment
kubectl apply -f k8s-deployment.yaml

# Verificar que está corriendo
kubectl get pods
kubectl get services

# Ver logs
kubectl logs -f deployment/servicio-bi
```

---

## 🔧 Testing con Docker Compose (Desarrollo Local)

### Opción 1: Usar Supabase + MongoDB Atlas (como en producción)

```bash
# Editar docker-compose.yml - comentar postgres y mongo locales
# Agregar tus URIs reales en environment

docker-compose up servicio-bi
```

### Opción 2: Levantar TODO localmente (PostgreSQL + MongoDB + API)

```bash
# Levanta postgres local, mongo local y tu API
docker-compose up

# Acceder a:
# - API: http://localhost:8000
# - PostgreSQL: localhost:5432
# - MongoDB: localhost:27017
```

### Detener servicios:
```bash
docker-compose down

# Borrar volúmenes (resetear bases de datos):
docker-compose down -v
```

---

## 📊 Comandos útiles

### Ver imágenes locales
```bash
docker images
```

### Ver contenedores corriendo
```bash
docker ps
```

### Eliminar imagen
```bash
docker rmi tuusuario/servicio-bi:latest
```

### Ver logs de contenedor
```bash
docker logs -f nombre_contenedor
```

### Entrar a un contenedor
```bash
docker exec -it nombre_contenedor /bin/bash
```

---

## 🎯 Resumen para defender ante el ingeniero

**"Implementamos Docker para:**
1. ✅ **Portabilidad:** La aplicación corre en cualquier ambiente (local, Render, Kubernetes)
2. ✅ **Consistencia:** El mismo contenedor funciona en desarrollo y producción
3. ✅ **Escalabilidad:** Kubernetes puede escalar múltiples replicas del servicio BI
4. ✅ **Aislamiento:** Dependencias encapsuladas en el contenedor
5. ✅ **CI/CD:** Imagen publicada en Docker Hub lista para deployar"**

**Flujo completo:**
```
Código → Dockerfile → Build → Push a Docker Hub → Pull en K8s → Deploy
```

**Ventajas técnicas:**
- Imagen inmutable y versionada
- Fácil rollback a versiones anteriores
- Compatible con orquestadores (Kubernetes, Docker Swarm)
- Independiente del sistema operativo del host
