# Sistema de Facturación (FastAPI + NiceGUI)

Aplicación web de facturación para Panamá con generación de facturas PDF, historial, duplicación y anulación, códigos QR de verificación y gestión de catálogo y pedidos B2B.

## Arranque Rápido

Lo único que necesitas instalado es Docker con Docker Compose.

```bash
git clone https://github.com/slade1930/Sistema-facturacion.git
cd Sistema-facturacion
git checkout desarrollo
cp .env.example .env
# Edita el archivo .env y define API_KEY y FACTURA_HMAC_KEY con tus propios valores
docker compose up --build
```
* Healthcheck: http://localhost:8000/health (debe devolver {"status":"ok"})
* Swagger UI: http://localhost:8000/docs

Nota: Para más detalles sobre la instalación, consulta la guía de despliegue.

Tecnologías
* Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic.
* Frontend: NiceGUI.
* Base de Datos: PostgreSQL.
* Infraestructura: Docker, Docker Compose.
* Pruebas: Pytest.
* PDF: Reportlab.
* Documentación

Toda la documentación técnica detallada se encuentra en la carpeta docs/:
* Arquitectura del sistema
* Base de datos y esquema
* Reglas de negocio
* Estructura del proyecto y ramas
* Tecnologías y versiones
