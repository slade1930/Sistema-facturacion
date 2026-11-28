# Backend del Sistema de facturación

Gente, acá está el servicio del sistema: **FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL**. Corre en Docker junto a la base y expone la API en `http://localhost:8000`. La interfaz Swagger UI de FastAPI está en `/docs`.

## Estructura de `backend/app`

- `api/`: routers y endpoints de la v1 (`/api/v1`), con dependencias de autenticación y sesión.
- `core/`: configuración (`settings`) y manejo centralizado de errores.
- `db/`: base y sesión de SQLAlchemy.
- `models/`: modelos ORM de facturación y catálogo.
- `repositories/`: acceso a datos (facturas, series, configuración, catálogo y pedidos).
- `schemas/`: modelos Pydantic de entrada y salida.
- `services/`: reglas de negocio (totales, ciclo de vida, numeración, verificación, PDF y pedidos).
- `utils/`: validadores, formateadores y guardado de logos.
- `ml/`: generador de datos de ejemplo y módulos de ML todavía en esqueleto.

## Levantarlo con Docker

Desde la raíz del repo:

```bash
cp .env.example .env
# Editá .env: API_KEY y FACTURA_HMAC_KEY son OBLIGATORIAS.
docker compose up --build -d
```

`docker-compose.yml` usa `${API_KEY:?...}` y `${FACTURA_HMAC_KEY:?...}`: si no las definís, el contenedor no arranca. `FACTURA_VERIFICACION_BASE_URL` tiene por defecto `http://localhost:8000`; en despliegue poné la **URL pública real**, porque `pdf.py` arma el QR con esa base.

Ver [variables de entorno](../docs/despliegue/variables-de-entorno.md), [instalación](../docs/despliegue/instalacion.md), [Docker](../docs/despliegue/docker.md) y [errores comunes](../docs/despliegue/errores-comunes.md).

## Migraciones y pruebas

Dentro del contenedor:

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic check
docker compose exec -T backend python -m pytest -q
```

Hay tres migraciones en `alembic/versions/`: `20261123_0001_inicial.py`, `20261123_0002_correcciones_fidelidad_original.py` y `20261123_0003_anomalias_factura.py` (head). Las pruebas están en cuatro carpetas: `tests/api`, `tests/models`, `tests/services` y `tests/ml`.

## Autenticación y errores

Salvo las dos rutas públicas, la API pide la cabecera `X-API-Key`. Las públicas son `GET /health` y `GET /api/v1/verificar/{numero_serie}/{codigo}`.

Todos los errores usan el mismo cuerpo: `{"detail": "...", "code": "..."}`. Los códigos que salen hoy son `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `VALIDATION_ERROR` y `RATE_LIMITED`.

## Portal de empresas

Las rutas de acceso son `POST /api/v1/auth/registro`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/yo` y `POST /api/v1/auth/cambiar-clave`. Registro y login son públicos; las demás necesitan `X-API-Key` y el token `Bearer`. Una API-Key válida sin token mantiene el comportamiento anterior solo para pruebas y procesos internos.

Con un token de empresa, el backend filtra catálogo por sector y clientes, pedidos, facturas, historial y PDF por la empresa del token. Un recurso ajeno da 404; un cuerpo que contradiga al token da 403. La configuración, las altas de catálogo y clientes, la facturación manual, anular, duplicar, facturar pedidos y el ML salvo recomendaciones son solo para admin o sistema.

El primer administrador se crea dentro del contenedor con:

```bash
python -m app.cli.crear_admin --usuario admin
```

Define `ADMIN_PASSWORD` en tu entorno antes de ejecutarla. La contraseña nunca se pasa como argumento: se lee de esa variable o se pide por consola. Debe tener entre 8 y 64 caracteres, al menos una mayúscula y al menos un número. Agrega `ADMIN_PASSWORD` a tu `.env` local; no hay valor por defecto en el repositorio. La cuenta queda marcada para cambiar la clave en el primer acceso.

## Rutas reales de la API (32)

**Pública**

- `GET /health`

**Catálogo y clientes**

- `GET /api/v1/categorias`
- `GET /api/v1/categorias/{categoria_id}`
- `POST /api/v1/categorias`
- `PUT /api/v1/categorias/{categoria_id}`
- `GET /api/v1/productos`
- `GET /api/v1/productos/{producto_id}`
- `POST /api/v1/productos`
- `PUT /api/v1/productos/{producto_id}`
- `DELETE /api/v1/productos/{producto_id}`
- `GET /api/v1/catalogo/buscar`
- `GET /api/v1/clientes`
- `GET /api/v1/clientes/{cliente_id}`
- `POST /api/v1/clientes`
- `PUT /api/v1/clientes/{cliente_id}`
- `DELETE /api/v1/clientes/{cliente_id}`

**Facturación**

- `POST /api/v1/facturas`
- `GET /api/v1/facturas/{factura_id}`
- `POST /api/v1/facturas/{factura_id}/duplicar`
- `POST /api/v1/facturas/{factura_id}/anular`
- `GET /api/v1/facturas/{factura_id}/pdf`

**Historial y verificación**

- `GET /api/v1/historial`
- `GET /api/v1/verificar/{numero_serie}/{codigo}` (pública)

**Pedidos B2B y carrito**

- `GET /api/v1/pedidos`
- `GET /api/v1/pedidos/por-facturar`
- `GET /api/v1/pedidos/{pedido_id}`
- `POST /api/v1/pedidos`
- `POST /api/v1/pedidos/{pedido_id}/facturar`
- `POST /api/v1/carrito/calcular`

**Configuración**

- `GET /api/v1/configuracion`
- `PUT /api/v1/configuracion`
- `POST /api/v1/configuracion/logo`

Hoy **no hay rutas `/ml` registradas**: la lista de `/openapi.json` es exactamente esa.

## Logo

`POST /api/v1/configuracion/logo` acepta PNG, JPG, JPEG y WEBP de hasta 5 MB. El nombre del usuario se ignora: se guarda un UUID en `backend/media` y la configuración guarda `media/<uuid>.<ext>`. Antes de escribir se valida con Pillow que los bytes sean una imagen real y que el formato coincida con la extensión; si no, da 422 y no queda archivo. Si un logo viejo llegara a estar dañado, el PDF se genera igual sin él y deja un aviso en el log.

## Módulo de ML

Ver [README de ML](app/ml/README.md). Hoy hay un generador reproducible y 5 CSV de ejemplo en `app/ml/datasets/generados/`; el resto (reglas, features, modelos, entrenamiento, evaluación, inferencia y los routers `/ml`) es esqueleto y ningún modelo está entrenado. Las dependencias van en `requirements-ml.txt` (scikit-learn, pandas, numpy, statsmodels y joblib) y `torch` CPU se instala aparte en `backend/Dockerfile`. Los modelos entrenados van en `backend/ml_models`, fuera de Git.

## Interfaz

La interfaz **NiceGUI ya está implementada** en `ui/`, con 13 rutas, cliente `httpx` server-side y servicio `ui` en Docker Compose en el puerto `8080`. No usa CORS ni JavaScript para consumir la API: las llamadas se hacen desde el servidor Python con la cabecera `X-API-Key`. Swagger UI de FastAPI sigue disponible en `/docs`.

## Enlaces y archivos vacíos

- [README del repo](../README.md)
- [Manual de usuario](../docs/manual/manual-de-usuario.md)
- [Arquitectura](../docs/tecnica/arquitectura.md)
- [Base de datos](../docs/tecnica/base-de-datos.md)
- [Estructura del proyecto](../docs/tecnica/estructura-proyecto.md)
- [Reglas de negocio](../docs/tecnica/reglas-de-negocio.md)
- [Tecnologías](../docs/tecnica/tecnologias.md)
- [Prueba rápida](../docs/despliegue/prueba.md)

Archivos de 0 bytes que siguen fuera de `__init__.py`, `.gitkeep` y `ui/`: **ninguno** (este README ya no está vacío). No hay `backend/pyproject.toml` versionado.
