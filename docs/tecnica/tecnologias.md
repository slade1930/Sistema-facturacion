# Tecnologías Utilizadas

El proyecto está desarrollado en **Python 3.12** y utiliza las siguientes librerías y herramientas, con las versiones exactas definidas en `backend/requirements.txt`:

*   **FastAPI:** `0.165.0` (Framework principal para la API).
*   **Uvicorn:** `0.54.0` (Servidor ASGI para correr FastAPI).
*   **SQLAlchemy:** `2.1.9` (ORM para la base de datos).
*   **Alembic:** `1.20.1` (Migraciones de base de datos).
*   **psycopg:** `3.3.9` (Driver para conectar con PostgreSQL).
*   **Pydantic Settings:** `2.16.3` (Manejo de variables de entorno y configuración).
*   **Pytest:** `9.2.0` (Framework para las pruebas unitarias).
*   **Reportlab:** `5.1.1` (Generación de los PDFs de las facturas).
*   **HTTPX:** `0.28.1` (Cliente HTTP para pruebas).
*   **python-multipart:** `0.0.33` (Manejo de formularios y subida de archivos).
*   **PostgreSQL:** Base de datos relacional (corre vía Docker).
*   **Docker y Docker Compose:** Para levantar el entorno completo.
*   **NiceGUI:** planeado para la interfaz; hoy `ui/` está vacío y no hay dependencia ni servicio en Docker. Por ahora se usa Swagger UI.
