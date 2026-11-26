# Docker y Docker Compose

El proyecto utiliza Docker Compose para facilitar el despliegue y la ejecución de los servicios necesarios para el funcionamiento del Sistema de Facturación.
La configuración se encuentra en el archivo `docker-compose.yml`, ubicado en la raíz del proyecto.

## 1. Servicios del sistema

El proyecto cuenta con dos servicios principales:

### 1.1. Servicio db

Este servicio utiliza PostgreSQL 16 mediante la imagen `postgres:16-alpine`.

Sus funcionalidades principales son:

- Crea y administra la base de datos del sistema.
- Configura el usuario, la contraseña y el nombre de la base de datos mediante variables de entorno.
- Utiliza un volumen para conservar los datos.
- Incluye un healthcheck que comprueba si PostgreSQL está preparado para aceptar conexiones.

### 1.2. Servicio backend

Este servicio contiene la API desarrollada con FastAPI.

Sus principales características son:

- Construye su imagen utilizando el Dockerfile de la carpeta `backend`.
- Espera a que el servicio de base de datos antes de inciar
- Ejecuta las migraciones de la base de datos mediante `alembic upgrade head`.
- Inicia la aplicación utilizando Uvicorn.
- Exponer el puerto 8000 para permitir el acceso al backend.
- Utilizar la variable DATABASE_URL para conectarse a PostgreSQL mediante el nombre del servicio db.
- Recibir las variables FACTURA_HMAC_KEY y API_KEY para la configuración de seguridad.

Además, utiliza un volumen para acceder a los modelos de aprendizaje automático almacenados en backend/ml_models.

## 2. Volumen de datos

Docker Compose utiliza los siguientes volúmenes:

2.1. Volumen postgres_data

Está asociado al directorio de almacenamiento de PostgreSQL:

`/var/lib/postgresql/data`

Permite conservar la información de la base de datos aunque se detengan o eliminen los contenedores.

2.2. Volumen de modelos

El backend utiliza la siguiente configuración:

`./backend/ml_models:/app/ml_models`

Permite acceder desde el contenedor a los modelos almacenados en la carpeta backend/ml_models del proyecto.

## 3. Comandos principales

Los siguientes comandos deben ejecutarse desde la carpeta raíz del proyecto.

### Iniciar los servicios

```bash
docker compose up
```

### Construir las imágenes e iniciar los servicios

```bash
docker compose up --build
```

### Consultar los contenedores activos

```bash
docker compose ps
```

### Consultar los registros de todos los servicios

```bash
docker compose logs
```

### Seguir los registros en tiempo real

```bash
docker compose logs -f
```

### Consultar los registros del backend

```bash
docker compose logs -f backend
```

### Consultar los registros de PostgreSQL

```bash
docker compose logs -f db
```

### Detener los servicios

```bash
docker compose down
```

Este comando detiene y elimina los contenedores y la red del proyecto, pero conserva el volumen de datos.

## 4. Eliminación de los datos locales

Para detener los servicios y eliminar también los volúmenes asociados, se utiliza:

```bash
docker compose down -v
```

**Advertencia:** Este comando elimina el volumen `postgres_data` y, por tanto, borra los datos de la base de datos local almacenados.

Debe utilizarse únicamente cuando se desee reiniciar la base de datos desde cero y se tenga claro que se perderá la información almacenada.

## Puntos clave a considerar:

- Docker Desktop debe estar iniciado antes de ejecutar los comandos.
- Los valores predeterminados de las variables de entorno son ejemplos para desarrollo.
- Se recomienda configurar las variables correspondientes en el archivo `.env` de la raíz.
- La variable API_KEY debe estar definida en el archivo .env de la raíz, ya que es necesaria para iniciar el backend.
- La variable FACTURA_HMAC_KEY se utiliza para configurar la clave de seguridad relacionada con la firma de facturas.
- Dentro de Docker, el backend utiliza el nombre del servicio db para conectarse a PostgreSQL.
- La carpeta backend/ml_models se monta dentro del contenedor para permitir el acceso a los modelos de aprendizaje automático.
