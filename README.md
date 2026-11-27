# Sistema de facturación

Versión en FastAPI de [Factura](https://github.com/moisesroyal/Factura). Por ahora levantamos lo mínimo: PostgreSQL + la API con un `/health` para comprobar que todo funciona. Los modelos, endpoints y pantallas los van armando los equipos.

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

La primera vez `--build` arma la imagen. En las siguientes podés usar `docker compose up -d` para dejarlo corriendo en segundo plano.

Antes de levantar, copiá `.env.example` a `.env` y definí `API_KEY` y `FACTURA_HMAC_KEY` con tus propios valores. Ambas son obligatorias: si falta alguna, la app no arranca. Si además querés cambiar los usuarios/claves de PostgreSQL, editá los otros valores en ese mismo `.env`. El `.env` real nunca se sube a git.

## Probar que levantó

- **http://localhost:8000/health** → debe devolver `{"status":"ok"}`
- **http://localhost:8000/docs** → documentación de FastAPI, con el endpoint `/health` para probar desde el navegador

Desde la terminal también podés comprobarlo:

```bash
curl http://localhost:8000/health
```

El servicio `backend` corre `alembic upgrade head` y recién después arranca uvicorn, así que cuando la API responde la base ya está al día.

## Comandos útiles

```bash
docker compose ps                  # ver el estado de los contenedores
docker compose logs -f backend     # logs de la API (Ctrl+C para salir)
docker compose logs db             # logs de PostgreSQL
docker compose down                # parar todo, conservando los datos de la base
docker compose down -v             # parar y borrar el volumen de la base (¡cuidado!)
```

Si el puerto 8000 está ocupado, cambiá en `docker-compose.yml` el mapeo `"8000:8000"` por `"8001:8000"` y entrás por `http://localhost:8001`.

## Migraciones

`backend/alembic/versions/` está vacío a propósito. Cuando el Equipo 1 agregue los modelos en `backend/app/models/`, genera la primera migración con:

```bash
docker compose exec backend alembic revision --autogenerate -m "primeras tablas"
docker compose exec backend alembic upgrade head
```

Alembic ya está enganchado a `Base.metadata` y a `settings.DATABASE_URL`, así que alcanza con importar los modelos nuevos en `backend/app/models/__init__.py`.

## Cómo trabajar

Cada equipo trabaja en su rama y trae lo nuevo con `git merge desarrollo`. Prohibido subir a `main` o directo a `desarrollo` sin pasar por Pull Request con revisión de un líder de otro equipo. Las versiones de `backend/requirements.txt` las cambian solo los líderes.
