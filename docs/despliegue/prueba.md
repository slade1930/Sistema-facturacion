# Pruebas automatizadas del backend

Explicación de cómo ejecutar las pruebas automatizadas del backend del sistema de facturación, dónde se encuentran organizadas y qué requisitos necesitan para ejecutarse correctamente.

El proyecto utiliza **pytest** para comprobar el funcionamiento de los modelos, servicios y componentes del backend.

Las pruebas se encuentran en el directorio backend/tests/ y están organizadas en carpetas según el componente que verifican.

¿Qué es pytest?
Pytest es una herramienta de Python utilizada para ejecutar pruebas automatizadas del backend. Permite comprobar que los diferentes componentes del sistema funcionan correctamente y detectar posibles errores durante el desarrollo.

En este proyecto se utiliza para ejecutar las pruebas ubicadas en backend/tests/, que verifican el comportamiento de los modelos y servicios del sistema de facturación.

## Requisitos

Para ejecutar las pruebas se necesitan:

- Docker y Docker Compose.
- Las dependencias especificadas en backend/requirements.txt, entre ellas pytest 9.2.0.

Entre las dependencias principales se encuentran SQLAlchemy, Alembic, psycopg y pytest.

## Ubicación de las pruebas

Las pruebas se encuentran dentro de `backend/tests/`, organizadas de la siguiente manera:

- backend/tests/models/ 
- backend/tests/services/
- backend/tests/conftest.py
- backend/tests/api/
- 
### Pruebas de modelos

La carpeta `models/` contiene pruebas relacionadas con los modelos y el acceso a la base de datos.

Se comprueba la existencia de las 10 tablas esperadas, la integridad y las restricciones de los modelos, las relaciones entre facturas, productos y pedidos, así como la configuración de conexión a PostgreSQL.

### Pruebas de servicios

La carpeta `services/` contiene pruebas relacionadas con la lógica y los servicios del sistema de facturación.

Se evalúan los cálculos y totales de facturación, la numeración de facturas, la conversión de números a letras, la generación de documentos PDF, el formateo y la validación de datos, las operaciones de catálogo y pedidos, y el código de verificación.

### Pruebas de API

La carpeta `api/` contiene pruebas relacionadas con los endpoints y la seguridad de la API del sistema de facturación.

Se verifican la autenticación mediante API Key, el estado de la API, las operaciones de creación, consulta, anulación y duplicación de facturas, el historial, el cálculo del carrito, la configuración del logotipo y la gestión y facturación de pedidos B2B.

### Archivo conftest.py

El archivo `conftest.py` contiene configuración compartida para pytest.

Agrega la carpeta `backend/` a la ruta de búsqueda de Python para que las pruebas puedan importar los módulos de la aplicación. Y registra la marca `integration`, utilizada para identificar pruebas de integración que requieren `DATABASE_URL`.

## Cómo ejecutar las pruebas con Docker

Para ejecutar las pruebas, primero es necesario tener Docker Desktop iniciado y ubicarse en la raíz del proyecto, donde se encuentra el archivo docker-compose.yml.

### Paso 1. Iniciar los contenedores

Ejecutar:

```bash
docker compose up -d --build
```

Este comando construye las imágenes necesarias e inicia los servicios definidos en Docker Compose.

### Paso 2. Ejecutar pytest

Ejecutar el siguiente comando:

```bash
docker compose exec backend pytest -v
```

Este comando ejecuta pytest dentro del contenedor `backend`.

La opción `-v` muestra los nombres de las pruebas y sus resultados.

### Paso 3. Revisar los resultados

Al finalizar, pytest muestra un resumen de las pruebas ejecutadas.

| Estado | Significado |
|---|---|
| `PASSED` | La prueba se ejecutó correctamente. |
| `FAILED` | La prueba se ejecutó, pero no cumplió una condición esperada. |
| `SKIPPED` | La prueba fue omitida por una condición definida en el código. |

## Pruebas que requieren DATABASE_URL

Algunas pruebas necesitan conectarse a PostgreSQL para comprobar el funcionamiento de la base de datos.

Por ejemplo, en `backend/tests/models/test_conexion.py` se encuentra la siguiente condición:

```python
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Sin DATABASE_URL"
)
def test_conexion_postgres():
    with get_engine().connect() as conexion:
        assert conexion.execute(text("SELECT 1")).scalar_one() == 1
```

La condición `skipif` indica que pytest debe omitir esta prueba cuando la variable de entorno `DATABASE_URL` no está definida.

Cuando esto ocurre, la prueba aparece como `SKIPPED`, con el motivo `Sin DATABASE_URL`. Esto no significa que haya fallado, sino que no se ejecutó porque no se cumplió el requisito de conexión.

### DATABASE_URL dentro de Docker

En la configuración de Docker Compose, el backend recibe la variable `DATABASE_URL` para conectarse al servicio de PostgreSQL.

La dirección utiliza el nombre del servicio `db` como host:

```env
DATABASE_URL=postgresql+psycopg://factura:factura@db:5432/factura
```

Si se ejecuta el backend directamente fuera de Docker, la dirección de conexión debe utilizar `localhost` cuando PostgreSQL está publicado en el equipo local:

```env
DATABASE_URL=postgresql+psycopg://factura:factura@localhost:5432/factura
```

Por tanto, las pruebas que requieren PostgreSQL necesitan que `DATABASE_URL` esté definida en el entorno del proceso que ejecuta pytest y que la base de datos esté disponible.
