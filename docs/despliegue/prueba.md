# Pruebas automatizadas del backend

Explicación de cómo ejecutar las pruebas automatizadas del backend del sistema de facturación, dónde se encuentran organizadas y qué requisitos necesitan para ejecutarse correctamente.

El proyecto utiliza **pytest** para comprobar el funcionamiento de los modelos, servicios y componentes del backend.

¿Qué es pytest?
Pytest es una herramienta de Python utilizada para ejecutar pruebas automatizadas del backend. Permite comprobar que los diferentes componentes del sistema funcionan correctamente y detectar posibles errores durante el desarrollo.

En este proyecto se utiliza para ejecutar las pruebas ubicadas en backend/tests/, que verifican el comportamiento de los modelos y servicios del sistema de facturación.

## Requisitos

Para ejecutar las pruebas se necesitan:

- Python 3.12.
- Docker y Docker Compose.
- Las dependencias especificadas en `backend/requirements.txt`.
- pytest 9.2.0.

Entre las dependencias principales se encuentran SQLAlchemy, Alembic, psycopg y pytest.

## Ubicación de las pruebas

Las pruebas se encuentran dentro de `backend/tests/`, organizadas de la siguiente manera:

- backend/tests/models/ 
- backend/tests/services/
- backend/tests/conftest.py


### Pruebas de modelos

La carpeta `models/` contiene pruebas relacionadas con los modelos y el acceso a la base de datos.

Incluye pruebas de conexión, integridad y relaciones entre los modelos.

### Pruebas de servicios

La carpeta `services/` contiene pruebas relacionadas con la lógica y los servicios del sistema de facturación.

Incluye pruebas de totales, series, generación de PDF, validaciones, conversión de números a letras y verificación.

### Archivo conftest.py

El archivo `conftest.py` contiene configuración compartida para pytest.

Agrega la carpeta `backend/` a la ruta de búsqueda de Python para que las pruebas puedan importar los módulos de la aplicación. Y registra la marca `integration`, utilizada para identificar pruebas de integración que requieren `DATABASE_URL`.

## Cómo ejecutar las pruebas con Docker

El proyecto permite ejecutar las pruebas dentro del contenedor del backend.

### Paso 1. Iniciar los contenedores

Desde la carpeta raíz del proyecto, ejecutar:

```bash
docker compose up -d --build
```

Este comando construye las imágenes necesarias e inicia los servicios definidos en Docker Compose.

### Paso 2. Ejecutar pytest

Ejecutar el siguiente comando:

```powershell
docker compose exec backend pytest -v
```

Este comando ejecuta pytest dentro del contenedor `backend`.

La opción `-v` muestra los nombres de las pruebas y sus resultados.

### Paso 3. Revisar los resultados

Al finalizar, pytest muestra un resumen de las pruebas ejecutadas.

Los resultados más comunes son:

- **PASSED:** la prueba se ejecutó correctamente.
- **FAILED:** la prueba encontró un error.
- **SKIPPED:** la prueba fue omitida por una condición establecida en el código.

## Variable DATABASE_URL y pruebas omitidas

Algunas pruebas necesitan conectarse a PostgreSQL para comprobar el funcionamiento de la base de datos.

Para ello utilizan la variable de entorno `DATABASE_URL`, que contiene la dirección de conexión.

Dentro de Docker Compose, el backend recibe automáticamente una dirección de conexión que utiliza el servicio `db` como host:

```text
postgresql+psycopg://factura:factura@db:5432/factura
```

Cuando se ejecuta el backend fuera de Docker, se utiliza `localhost` como host, según la configuración de `backend/.env.example`.

### ¿Por qué algunas pruebas se omiten?

No todas las pruebas necesitan una conexión real con PostgreSQL.

Por ejemplo, en `backend/tests/models/test_conexion.py` existe una prueba llamada `test_conexion_postgres`, que realiza una consulta `SELECT 1` para comprobar la conexión.

Esta prueba utiliza la siguiente condición:

```python
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Sin DATABASE_URL"
)
```

Esto significa que:

- Si `DATABASE_URL` está configurada, la prueba intenta conectarse a PostgreSQL.
- Si `DATABASE_URL` no está configurada, pytest omite automáticamente esa prueba.
- Las pruebas que no necesitan PostgreSQL pueden ejecutarse sin esa conexión.

La omisión no significa necesariamente que exista un error en el sistema; significa que no se cumplen las condiciones necesarias para ejecutar esa prueba.

**Importante:** al ejecutar las pruebas fuera de Docker, definir `DATABASE_URL` en un archivo `.env` no garantiza que esté disponible para `os.getenv()`. La variable debe estar exportada en el entorno del proceso que ejecuta pytest.
