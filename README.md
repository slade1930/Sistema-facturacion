# Sistema de Facturación (FastAPI + NiceGUI)

Aplicación web de facturación para Panamá con generación de facturas PDF, historial, duplicación y anulación, códigos QR de verificación y gestión de catálogo y pedidos B2B.

Versión en FastAPI de [Factura](https://github.com/moisesroyal/Factura).

## Levantar el proyecto

Lo único que necesitás instalado es Docker con Docker Compose. Las dependencias de Python van dentro del contenedor, así que no hace falta crear un virtualenv.

```bash
git clone https://github.com/slade1930/Sistema-facturacion.git
cd Sistema-facturacion
git checkout desarrollo
git pull
cp .env.example .env
docker compose up --build
```

La primera vez `--build` arma la imagen. Después podés usar `docker compose up -d` para dejarlo corriendo en segundo plano.

Antes de levantar, copiá `.env.example` a `.env` y definí `API_KEY` y `FACTURA_HMAC_KEY` con tus propios valores. **Ambas son obligatorias**: si falta alguna, la app no arranca. Compose ya no pone defaults para `FACTURA_HMAC_KEY` y el valor viejo de desarrollo quedó rechazado. Reemplazá el placeholder `cambia_esta_clave`. Si querés cambiar usuarios/claves de PostgreSQL, editá los otros valores en ese mismo `.env`. El `.env` real nunca se sube a git.

Para más detalle, mirá [variables de entorno](docs/despliegue/variables-de-entorno.md) y [instalación](docs/despliegue/instalacion.md).

## Probar que levantó

- **http://localhost:8000/health** → debe devolver `{"status":"ok"}`
- **http://localhost:8000/docs** → documentación de FastAPI, con `/health` para probar desde el navegador

```bash
curl http://localhost:8000/health
```

Si algo falla, revisá [errores comunes](docs/despliegue/errores-comunes.md).

## Crear el administrador

1. Definí tus propios valores en `.env`. Para la creación podés exportar `ADMIN_PASSWORD` en tu terminal; si no la definís, la CLI te la pedirá de forma interactiva. No escribas ese valor en un archivo versionado ni lo pases como argumento.
2. Con los contenedores levantados, ejecutá:

   ```bash
   docker compose exec backend python -m app.cli.crear_admin --usuario nombre-elegido
   ```

3. Entrá a `http://localhost:8080/login`, iniciá sesión con ese usuario y completá el cambio de clave que se pide en el primer acceso.

## Registrar una empresa de prueba

1. Abrí `http://localhost:8080/registro`.
2. Completá nombre de la empresa, RUC, correo, dirección, teléfono, sucursal, sector (`tecnologia`, `turismo` o `supermercado`) y una contraseña de tu elección que cumpla la política: entre 8 y 64 caracteres, con al menos una mayúscula y un número. No hay valores por defecto.
3. Al guardar se inicia sesión y se abre `/portal/inicio`. En `/portal/catalogo` solo aparecen productos de tu sector.
4. Agregá productos al carrito y confirmá la compra. El pedido y la factura se crean juntos; la factura aparece en `/portal/facturas` con detalle y descarga de PDF.

## Comandos útiles

```bash
docker compose ps                  # ver el estado de los contenedores
docker compose logs -f backend     # logs de la API (Ctrl+C para salir)
docker compose logs db             # logs de PostgreSQL
docker compose down                # parar todo, conservando los datos
docker compose down -v             # parar y borrar el volumen de la base (¡cuidado!)
```

Si el puerto 8000 está ocupado, cambiá en `docker-compose.yml` el mapeo `"8000:8000"` por `"8001:8000"`.

## Migraciones

`backend/alembic/versions/` ya contiene las migraciones `0001`, `0002` y `0003`. La `0003` agrega `en_revision`, `puntaje_anomalia` y `motivo_anomalia` en `factura`. El servicio `backend` corre `alembic upgrade head` antes de arrancar uvicorn, así que cuando la API responde la base ya está al día.

Para una migración nueva:

```bash
docker compose exec backend alembic revision --autogenerate -m "nombre"
docker compose exec backend alembic upgrade head
```

Solo el Equipo 1 crea migraciones; los módulos de ML las piden. Ver [base de datos](docs/tecnica/base-de-datos.md).

## Pruebas

```bash
cd backend
# Si aparecen bloqueos de .pyd:
#   Windows PowerShell: $env:SQLALCHEMY_NO_CEXTENSIONS='1'
#   Linux/macOS:        export SQLALCHEMY_NO_CEXTENSIONS=1
python -m pytest tests -q
```

El test de conexión se omite si no definís `DATABASE_URL`. Guía completa en [pruebas](docs/despliegue/prueba.md).

## Cómo trabajar

Cada equipo trabaja en su rama y trae lo nuevo con `git merge desarrollo`. Prohibido subir directo a `main` o a `desarrollo` sin Pull Request con revisión de un líder de otro equipo. Las versiones de `backend/requirements.txt` las cambian solo los líderes. El `router.py` lo edita solo Moisés (Equipo 4).

## Tecnologías

- Backend: Python, FastAPI, SQLAlchemy, Alembic.
- Interfaz: NiceGUI en `ui/` (13 rutas, cliente `httpx` server-side y 71 pruebas de UI). Swagger UI de FastAPI sigue disponible en `/docs`.
- Base de datos: PostgreSQL.
- Infraestructura: Docker, Docker Compose.
- Pruebas: pytest.
- PDF: Reportlab.

## Documentación

- [Arquitectura del sistema](docs/tecnica/arquitectura.md)
- [Base de datos y esquema](docs/tecnica/base-de-datos.md) — diagrama: `docs/tecnica/esquema_facturacion_estilo_final.drawio`
- [Reglas de negocio](docs/tecnica/reglas-de-negocio.md)
- [Estructura del proyecto y ramas](docs/tecnica/estructura-proyecto.md)
- [Tecnologías y versiones](docs/tecnica/tecnologias.md)
- [Instalación](docs/despliegue/instalacion.md) y [Docker](docs/despliegue/docker.md)
- [Variables de entorno](docs/despliegue/variables-de-entorno.md)
- [Guía para ejecutar las pruebas](docs/despliegue/prueba.md)
- [Errores comunes](docs/despliegue/errores-comunes.md)
- [Manual de usuario](docs/manual/manual-de-usuario.md)
