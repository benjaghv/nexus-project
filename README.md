# 🚀 Nexus Hub

**Nexus** es un interceptor de webhooks en tiempo real diseñado para capturar, visualizar y debugear integraciones de API. Permite a los desarrolladores inspeccionar payloads entrantes al instante sin configurar herramientas complejas, facilitando el monitoreo de flujos de datos entre sistemas heterogéneos.

### 🛠️ Tech Stack
* **Backend:** FastAPI (Python)
* **Real-time:** WebSockets
* **DB:** SQLite (Persistencia ligera para auditoría)
* **Infra:** Docker & Docker Compose

### 🚀 Instalación Rápida
Solo necesitas tener **Docker** instalado. Ejecuta el siguiente comando en la raíz del proyecto para levantar el entorno completo:

```bash
docker compose up --build
```
### 📋 Cómo usarlo
**Dashboard:** Accede a http://localhost:8000 para ver el feed en vivo.

**API Docs:** Revisa la documentación interactiva en http://localhost:8000/docs.

**Prueba:** Envía un POST a http://localhost:8000/webhook para ver la captura en tiempo real.
