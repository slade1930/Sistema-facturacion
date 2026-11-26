# Variables de entorno

El sistema de facturación utiliza variables de entorno para configurar la conexión con la base de datos y los parámetros de seguridad de la aplicación.

El proyecto cuenta con dos archivos de ejemplo para configurar las variables de entorno:

.env.example (raíz del proyecto): contiene las variables necesarias para configurar el entorno utilizado por Docker Compose, incluyendo la conexión con PostgreSQL y las claves de seguridad.

backend/.env.example: contiene las variables necesarias para configurar el backend cuando se ejecuta directamente fuera de Docker.

Para utilizar estos archivos, se debe crear una copia llamada `.env` y configurar los valores necesarios.

## 1. Variables del archivo .env.example (raíz)

| Variable | Descripción | Valor de ejemplo |
|---|---|---|
| POSTGRES_USER | Usuario utilizado para acceder a PostgreSQL. | factura |
| POSTGRES_PASSWORD | Contraseña del usuario de PostgreSQL. | factura |
| POSTGRES_DB | Nombre de la base de datos que utilizará PostgreSQL. | factura |
| DATABASE_URL | Dirección de conexión que utiliza el backend dentro de Docker. El host es el servicio `db`. | postgresql+psycopg://factura:factura@db:5432/factura |
| FACTURA_HMAC_KEY | Clave secreta utilizada para firmar y verificar los códigos de las facturas. | cambia_esta_clave_hmac_larga |

## 2. Variables del archivo backend/.env.example

| Variable | Descripción | Valor de ejemplo |
|---|---|---|
| DATABASE_URL | Dirección de conexión a PostgreSQL cuando el backend se ejecuta fuera de Docker. El host es `localhost`. | postgresql+psycopg://factura:factura@localhost:5432/factura |
| FACTURA_HMAC_KEY | Clave secreta utilizada para firmar y verificar los códigos de las facturas. | cambia_esta_clave_hmac_larga |
| FACTURA_HMAC_KEY | Clave secreta utilizada para firmar y verificar los códigos de las facturas. | cambia_esta_clave_hmac_larga |

## 3. Importancia de FACTURA_HMAC_KEY

La variable `FACTURA_HMAC_KEY` contiene una clave secreta utilizada para los mecanismos de firma y verificación de las facturas.

Cada desarrollador debe configurar su propia clave en su archivo `.env`.

**Advertencias de seguridad:**

- Nunca se debe subir la clave real al repositorio.
- No se deben compartir claves secretas públicamente.
- El valor incluido en `.env.example` es solamente ilustrativo.
- Para un entorno real se debe utilizar una clave larga, aleatoria y privada.

## 4. Diferencia entre los valores de DATABASE_URL

El valor de `DATABASE_URL` depende de dónde se ejecute el backend:

- Dentro de Docker: utiliza `db` como nombre del host.
- Fuera de Docker: utiliza `localhost` como nombre del host.

Es importante utilizar la dirección correspondiente al entorno de ejecución para evitar errores de conexión con PostgreSQL.
