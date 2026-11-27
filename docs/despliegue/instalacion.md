# Guía de instalación del sistema de facturación

Se describen los requisitos y pasos necesarios para instalar y ejecutar el Sistema de Facturación, desarrollado con FastAPI y PostgreSQL.

El proyecto utiliza Docker Compose para iniciar los servicios del sistema, facilitando la configuración y ejecución del backend y la base de datos.

## 1. Requisitos previos

Antes de iniciar la instalación, se deben tener disponibles las siguientes herramientas:

- **Git:** para obtener y clonar el repositorio del proyecto.
- **Docker Desktop:** para ejecutar los contenedores.
- **Docker Compose:** para administrar los servicios del proyecto. Está incluido en las versiones actuales de Docker Desktop.
- **Python 3.12.x:** versión requerida para el desarrollo local del backend directamente en el entorno local, sin utilizar contenedores. No es necesario instalarlo para ejecutar el proyecto mediante Docker.

## 2. Obtener el proyecto

Para obtener el proyecto, se debe clonar el repositorio desde GitHub:

```bash
git clone https://github.com/slade1930/Sistema-facturacion.git
```

Luego, ingresar a la carpeta del proyecto:

```bash
cd Sistema-facturacion
```

Finalmente, cambiar a la rama correspondiente al desarrollo del proyecto:

git checkout desarrollo

Nota: La rama puede cambiar según las instrucciones del equipo de desarrollo.

## 3. Configurar las variables de entorno

El proyecto utiliza variables de entorno para configurar la conexión con la base de datos y otros parámetros necesarios para el funcionamiento del sistema.

Para configurar el entorno local:

1. Localizar el archivo `.env.example` proporcionado por el proyecto.
2. Crear una copia del archivo con el nombre `.env`.
3. Configurar los valores necesarios según el entorno de ejecución.
4. Verificar que las claves y credenciales reales no se compartan ni se suban al repositorio.

**Importante:** No se deben publicar claves secretas, contraseñas ni valores reales de configuración.

## 4. Ejecutar el sistema

Para iniciar el sistema utilizando Docker Compose, ejecutar el siguiente comando desde la carpeta raíz del proyecto:

```bash
docker compose up --build
```

Este comando construye las imágenes necesarias e inicia los servicios definidos en el archivo `docker-compose.yml`.

La primera ejecución puede tardar unos minutos mientras Docker descarga las imágenes e instala las dependencias.

Esperar a que los contenedores terminen de iniciar y comprobar que no aparezcan errores durante el proceso.

**Nota:** Es necesario tener Docker Desktop iniciado antes de ejecutar el comando.

## 5. Comprobar que el sistema funciona

Una vez iniciado el sistema, se puede comprobar su funcionamiento mediante los siguientes endpoints:

- **Estado del servicio:** `http://localhost:8000/health`
- **Documentación de la API:** `http://localhost:8000/docs`

El endpoint `/health` permite verificar el estado del servicio y `/docs` permite consultar la documentación interactiva de la API.

Si ambos endpoints responden correctamente, el servicio está disponible para realizar pruebas.

## 6. Detener el sistema

Para detener los servicios del sistema sin eliminar los datos almacenados en la base de datos, ejecutar desde la carpeta raíz del proyecto:

```bash
docker compose down
```

Este comando detiene y elimina los contenedores y la red creados por Docker Compose, pero conserva los datos almacenados en los volúmenes.

**Importante:** No utilizar `docker compose down -v` si se desea conservar la información de la base de datos, ya que este comando elimina también los volúmenes asociados.
