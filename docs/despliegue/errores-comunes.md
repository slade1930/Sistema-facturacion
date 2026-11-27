# Errores comunes

Se reúne problemas reproducidos y comprobados durante el desarrollo del sistema de facturación, junto con las soluciones aplicadas por los equipos. Su objetivo es ayudar a identificar y resolver dificultades relacionadas con las dependencias, las pruebas automatizadas, el entorno de desarrollo y la integración de cambios.

## 1. Dependencias 

### 1.1. Pytest no estaba incluido en las dependencias

Al instalar las dependencias desde `backend/requirements.txt`, no era posible ejecutar las pruebas porque pytest no estaba incluido en el archivo

Para solucionarlo, se agregó la siguiente dependencia en el commit `d85e02c`:

```text
pytest==9.2.0
```

### 1.2. Bloqueo de archivos `.pyd` 

Al ejecutar las pruebas, se encontraron bloqueos de archivos `.pyd` durante la importación de SQLAlchemy y Pydantic

Se reportó dos alternativas para continuar:

- Configurar en la terminal (sólo si aparecen bloqueos `.pyd`):

```bash
# Windows PowerShell:
$env:SQLALCHEMY_NO_CEXTENSIONS="1"

# Linux/macOS:
export SQLALCHEMY_NO_CEXTENSIONS=1
```

- Ejecutar las pruebas dentro del contenedor Docker

### 1.3. Advertencias LF y CRLF en Windows

Al ejecutar `git add` pueden aparecer advertencias sobre la conversión de finales de línea de LF a CRLF.

Estos mensajes durante la preparación de archivos para Git. Son advertencias informativas y no afectaron el código ni las pruebas.

## 2. Base de datos 

### 2.1. Pruebas omitidas por falta de DATABASE_URL

Al ejecutar pytest sin configurar `DATABASE_URL`, las pruebas que necesitan conectarse a PostgreSQL se omiten cuando tienen configurada esa condición.

Por ejemplo, la prueba `test_conexion_postgres` utiliza `skipif` para comprobar si existe la variable.

Para ejecutarla, se debe configurar `DATABASE_URL` con una dirección válida y asegurarse de que PostgreSQL esté disponible.

## 3. Git e integración de cambios

### 3.1. Error al ejecutar comandos Git fuera del repositorio

Al ejecutar comandos Git desde una carpeta que no pertenece al repositorio aparece el mensaje:

```text
fatal: not a git repository
```

Se encontró esta situación al trabajar desde una ubicación incorrecta. Para evitarla, se debe situar en la raíz del repositorio antes de ejecutar los comandos.

### 3.2. Conflicto de merge al integrar cambios de desarrollo

Al integrar los cambios de la rama `desarrollo` en la rama `postgres`, se presentaron conflictos en cinco archivos.

Se resolvió los conflictos y validó la integración. Posteriormente, el Pull Request dejó de mostrar el mensaje «No se puede fusionar automáticamente».

### 3.3. TypeError después de integrar cambios en `numero_a_letras.py`

Después de integrar una nueva versión de `numero_a_letras.py`, dos pruebas fallaron porque seguían enviando el parámetro `prefijo` a `monto_a_letras_factura()`.

La nueva implementación establecía el prefijo `"SON:"` directamente y ya no aceptaba ese parámetro.

Se actualizó las dos pruebas en el commit `026afb1`. El resultado pasó de 130 aprobadas y 2 fallidas a 132 aprobadas, 1 omitida y ningún fallo.

### 3.4. Conflictos en archivos de infraestructura

Al integrar cambios de la rama `desarrollo`, pueden aparecer conflictos en archivos de infraestructura que impidan completar la integración automáticamente.

Se recomienda revisar los archivos afectados, resolver las diferencias y comprobar que la configuración resultante sea coherente con el proyecto.

## 4. Otras situaciones que pueden presentarse

También se mencionaron las siguientes situaciones durante el desarrollo. Se incluyen como referencias, aunque no se dispone de información suficiente para confirmar una solución específica aplicada en cada caso.

### 4.1. Variable FACTURA_HMAC_KEY no configurada

El servicio de verificación necesita `FACTURA_HMAC_KEY` para generar y validar los códigos HMAC de las facturas. Si la variable no está configurada, el servicio genera un `RuntimeError` y no continúa con la operación.

Se debe comprobar que esté definida en el entorno donde se ejecuta el backend.

### 4.2. Puerto ocupado

Al iniciar Docker, puede aparecer un error si el puerto requerido ya está siendo utilizado por otro proceso.

Se recomienda identificar qué servicio utiliza el puerto y revisar la configuración antes de volver a iniciar los contenedores.

### 4.3. Base de datos desactualizada después de cambios en los modelos

Después de modificar los modelos, la estructura de la base de datos puede no coincidir con la esperada por la aplicación.

Se recomienda comprobar las migraciones de Alembic y aplicar las que correspondan. Si se necesita reconstruir la base de datos desde cero, se pueden utilizar:

```bash
docker compose down -v
docker compose up --build
```

**Importante:** `docker compose down -v` elimina los volúmenes y puede borrar los datos almacenados en PostgreSQL. Debe utilizarse únicamente cuando se tenga la intención de eliminar esos datos.

### 4.4. Versión de Python diferente a la requerida

Utilizar una versión distinta a la establecida para el proyecto puede ocasionar incompatibilidades con las dependencias.

Se debe comprobar la versión indicada en los requisitos. Se utilizó Python 3.12.10 para ejecutar sus pruebas.

### 4.5. Inconsistencias en el código de verificación HMAC

Durante el desarrollo fue necesario establecer los campos y el orden utilizados para generar y validar los códigos de las facturas.

Para evitar inconsistencias, ambos procesos deben utilizar la misma secuencia:

```text
numero_serie | total_normalizado | cliente_ruc
```

El total debe normalizarse a dos decimales y el código debe respetar el formato establecido por el servicio.
