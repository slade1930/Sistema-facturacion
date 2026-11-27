# ML — estado real y reparto del equipo

Gente, acá ya no hay un esqueleto sin más: **los datos de ejemplo están listos y probados** y el Módulo 4 ya tiene catálogo, línea base, red local y evaluación del asistente; lo demás (reglas, features, inferencia, endpoints y los otros modelos) está por hacer. Este archivo es la fuente de verdad del equipo.

## 1. Estado real

Listo:

- `datasets/generar_datos.py`: generador reproducible, semilla fija `20261126`, 30 meses de historia, estacionalidad y casos raros inyectados.
- 5 CSV en `datasets/generados/`: **1000 facturas**, **2521 líneas de factura**, **400 pedidos**, **830 líneas de pedido** y **55 etiquetas de anomalías**.
- 113 pruebas en `tests/ml/` (112 pasan y 1 se salta: 1 de entorno, 1 de estructura, 19 del generador y 92 del Módulo 4).

Ya implementado del Módulo 4: `asistente/catalogo.py`, `asistente/intenciones.py`, `asistente/frases_entrenamiento.py`, `modelos/asistente.py`, `entrenamiento/entrenar_asistente.py` y `evaluacion/asistente.py`. Por hacer: `reglas/`, `features/`, `inferencia/` y los 4 routers de `api/v1/endpoints/ml/` siguen siendo stubs (docstrings) o no existen todavía; lo mismo los otros módulos de `evaluacion/`. El único modelo entrenable hoy es la red local del asistente: se entrena con `python -m app.ml.entrenamiento.entrenar_asistente` y queda en `backend/ml_models/asistente.pt` (fuera de Git).

Cómo generar y validar (dentro del contenedor):

```
python -m app.ml.datasets.generar_datos
python -m app.ml.datasets.generar_datos --validar
```

También se pueden correr con `docker compose exec -T backend python -m app.ml.datasets.generar_datos [--validar]`.

## 2. Política de los CSV versionados

- Los 5 CSV de `datasets/generados/` están versionados **TEMPORALMENTE** para que todos arranquen con los mismos datos. No se quitan ni se cambian las reglas de `.gitignore` sobre ellos.
- Todos son de ejemplo (`es_ejemplo=True`, marca `[DATOS DE EJEMPLO]`), **nunca datos reales**.
- Se borran en un commit aparte cuando los 3 módulos confirmen que los tienen o saben regenerarlos (semilla fija `20261126`).
- Las pruebas **no deben depender** de los CSV versionados: deben generar datos en una carpeta temporal (`tmp_path`).

## 3. Reglas del ML

- **El ML sugiere, no decide.** La app funciona sin modelos: sin modelo = "sin evaluar" o un valor simple.
- Siempre comparar contra una línea base simple y documentar las métricas acá, en la sección de cada módulo.
- Modelos entrenados van en `backend/ml_models/`, **fuera de Git**.
- Nada de datos reales ni de clientes a servicios externos.

## 4. Dependencias

- Sólo las de `requirements-ml.txt`: scikit-learn, pandas, numpy, statsmodels y joblib. No se editan `requirements.txt`, `requirements-ml.txt` ni `pyproject.toml` sin aprobación.
- `torch` CPU se instala aparte en `backend/Dockerfile`. Quien corra fuera de Docker debe instalarlo a mano.
- **No se agrega ninguna otra**: `mlxtend` NO está autorizado (las reglas de asociación se hacen con pandas) y el asistente NO usa `transformers` ni modelos descargados de internet.
- Las dependencias nuevas se piden a los líderes por Issue.

## 5. Contrato de los endpoints

- Respuesta: `{"evaluado": bool, "modelo": "...", "resultado": {...}}`.
- Errores con `app/core/errors.py`: `{"detail": "...", "code": "..."}` (nada de `detalle`).
- `db.commit()` **solo en el endpoint**.
- `router.py` lo edita **solo Moisés** (Equipo 4) al registrar cada router cuando el módulo esté listo.

## 6. Anomalías

- `puntaje_anomalia` va en escala **0 a 100**.
- El módulo escribe **solo** `en_revision`, `puntaje_anomalia` y `motivo_anomalia`; **no cambia** el `estado` `emitida`/`anulada`.
- El umbral lo fija Flinn con las métricas y lo documenta acá.

## 7. Ramas de trabajo

Ya creadas desde `ml`: `ml-anomalias`, `ml-pronostico`, `ml-recomendaciones` y `ml-asistente`.

- PR hacia `ml`, chicos y de un solo tema.
- Revisan **Flinn** y **Fernando**; quien coordina no aprueba lo suyo.
- Cada persona edita **SOLO sus archivos** y agrega su propia sección de métricas en este README (no edita la de otros).
- Nombres de prueba ÚNICOS (en `backend/tests/ml/` no hay `__init__.py`):

`test_reglas_anomalias.py`, `test_modelo_anomalias.py`, `test_evaluacion_anomalias.py`, `test_api_anomalias.py`, `test_features_pronostico.py`, `test_modelo_pronostico.py`, `test_modelo_pronostico_lstm.py`, `test_evaluacion_pronostico.py`, `test_api_pronostico.py`, `test_reglas_recomendaciones.py`, `test_modelo_recomendaciones.py`, `test_evaluacion_recomendaciones.py`, `test_api_recomendaciones.py`, `test_asistente_catalogo.py`, `test_asistente_intenciones.py`, `test_modelo_asistente.py`, `test_evaluacion_asistente.py`, `test_api_asistente.py`.

## 8. Reparto por módulo y persona

| Persona | Rama | Tarea | Archivos | Pruebas | Listo cuando |
|---|---|---|---|---|---|
| Antony | `ml-anomalias` (Módulo 1) | Reglas base (percentil de monto, descuento sobre umbral, duplicados por cliente+fecha+total, anulaciones repetidas por cliente) y revisión de seguridad | `app/ml/reglas/anomalias.py`, `app/ml/features/anomalias.py` | `test_reglas_anomalias.py` | Reglas andan sin entrenar, con la línea base documentada y revisadas por él. |
| Flinn | `ml-anomalias` (Módulo 1) | Isolation Forest, evaluación contra las 55 etiquetas (precisión, recall y F1; reglas vs modelo), umbral de `en_revision` y métricas acá | `app/ml/modelos/anomalias.py`, `app/ml/entrenamiento/entrenar_anomalias.py`, `app/ml/evaluacion/anomalias.py` | `test_modelo_anomalias.py`, `test_evaluacion_anomalias.py` | Umbral fijado y comparación reglas vs modelo escrita en el README. |
| Moisés | `ml-anomalias` (Módulo 1) | `POST /ml/anomalias/evaluar/{factura_id}` con `FacturaRepository`; escribe solo `en_revision`, `puntaje_anomalia`, `motivo_anomalia`; hook opcional y no bloqueante al crear factura; registra el router | `app/api/v1/endpoints/ml/anomalias.py`, `app/api/v1/router.py` | `test_api_anomalias.py` | Ruta registrada por él, `estado` intacto y `db.commit()` sólo en el endpoint. |
| Andres | `ml-pronostico` (Módulo 2) | Features por mes, producto y categoría; modelo clásico Holt-Winters o SARIMA y su entrenamiento. Junto con Cristian mantiene `generar_datos.py` | `app/ml/features/pronostico.py`, `app/ml/modelos/pronostico.py`, `app/ml/entrenamiento/entrenar_pronostico.py`, `app/ml/datasets/generar_datos.py` | `test_features_pronostico.py`, `test_modelo_pronostico.py` | Serie agregada reproducible y MAE/RMSE/sMAPE del clásico documentados. |
| Cristian | `ml-pronostico` (Módulo 2) | LSTM en PyTorch CPU y su entrenamiento. Junto con Andres mantiene `generar_datos.py` | `app/ml/modelos/pronostico_lstm.py`, `app/ml/entrenamiento/entrenar_pronostico_lstm.py`, `app/ml/datasets/generar_datos.py` | `test_modelo_pronostico_lstm.py` | Modelo entrenado con separación temporal, guardado en `backend/ml_models/`. |
| Joan | `ml-pronostico` (Módulo 2) | Evaluación con separación TEMPORAL (nunca al azar), MAE/RMSE/sMAPE contra "mismo mes del año anterior" y media móvil; endpoint `GET /ml/pronostico?meses=&producto_id=`; cargador de modelos | `app/ml/evaluacion/pronostico.py`, `app/api/v1/endpoints/ml/pronostico.py`, `app/ml/inferencia/cargador.py` | `test_evaluacion_pronostico.py`, `test_api_pronostico.py` | Comparación documentada, sin modelo = `None`, ruta lista para registrar. |
| Jesús | `ml-recomendaciones` (Módulo 3) | Línea base "más vendidos" y reglas de asociación (soporte, confianza, lift) con pandas | `app/ml/features/recomendaciones.py`, `app/ml/reglas/recomendaciones.py` | `test_reglas_recomendaciones.py` | Reglas y respaldo funcionando sin entrenar, con métricas de la línea base acá. |
| makirvy | `ml-recomendaciones` (Módulo 3) | Autoencoder en PyTorch sobre la matriz cliente-producto | `app/ml/modelos/recomendaciones.py`, `app/ml/entrenamiento/entrenar_recomendaciones.py` | `test_modelo_recomendaciones.py` | Modelo entrenado con datos de ejemplo y guardado fuera de Git. |
| mdeh25-droid | `ml-recomendaciones` (Módulo 3) | Evaluación (esconder un producto por pedido; hit rate y precision@5 contra la línea base) y `GET /ml/recomendaciones?producto_ids=1,2,3`, sin inactivos ni los que ya están en el carrito | `app/ml/evaluacion/recomendaciones.py`, `app/api/v1/endpoints/ml/recomendaciones.py` | `test_evaluacion_recomendaciones.py`, `test_api_recomendaciones.py` | Top 5 comparado con "más vendidos" y filtros probados. |
| Fernando | `ml-asistente` (Módulo 4) | Catálogo de 6 consultas predefinidas (ventas por mes, por cliente y por producto; facturas anuladas; top productos; facturas en revisión) que llaman a repositorios existentes y NUNCA a SQL generado; clasificador de intención por palabras clave y fechas; entrenamiento de la red pequeña | `app/ml/asistente/catalogo.py`, `app/ml/asistente/intenciones.py`, `app/ml/entrenamiento/entrenar_asistente.py` | `test_asistente_catalogo.py`, `test_asistente_intenciones.py` | Catálogo y línea base andan sin modelo; revisión de Antony. |
| Luis | `ml-asistente` (Módulo 4) | Modelo local = red pequeña en PyTorch (bolsa de palabras → capa oculta → 6 intenciones) entrenada con frases de ejemplo, sin descargar nada; evaluación contra la línea base de palabras clave; `POST /ml/asistente/consultar` con respuesta desde datos reales y "no entendí" si la confianza es baja | `app/ml/modelos/asistente.py`, `app/ml/asistente/frases_entrenamiento.py`, `app/ml/evaluacion/asistente.py`, `app/api/v1/endpoints/ml/asistente.py` | `test_modelo_asistente.py`, `test_evaluacion_asistente.py`, `test_api_asistente.py` | Respuesta desde repositorios reales, sin servicios externos, con "no entendí". |

El Módulo 4 depende de los módulos 1 a 3 (en revisión, anomalías) y de la revisión de Antony. El catálogo y el clasificador pueden avanzar ya sin modelo.

### Módulo 4 — asistente (Fernando y Luis)

Métricas con semilla fija `20261126`, 54 frases de entrenamiento (9 por intención) y 12 de validación separadas (2 por intención, sin solapamiento con las de entrenamiento):

| Evaluación | Línea base (palabras clave) | Red local |
|---|---|---|
| Frases de entrenamiento | — | 54/54 |
| Frases de validación | 10/12 (83,3 %) | 12/12 (100 %) |

- Los siete casos que Flinn marcó como FAIL en la revisión devuelven ahora la intención correcta y los parámetros del propio texto: `ventas por mes en octubre de 2026` → `{mes: 10, anio: 2026}`; `ventas de este año` → `{anio: 2026}`; `ventas por cliente Acme` → `{cliente: "acme"}`; `Ventas del cliente 3` → `{cliente_id: 3}`; `facturas anuladas en 2026` → `{anio: 2026}`; `top 3 productos en 2026` → `{anio: 2026, n: 3}`; `facturas en revisión` → `{}`.
- Dos entrenamientos seguidos producen exactamente los mismos pesos (`torch.manual_seed(20261126)` dentro de `ajustar()`); con otra semilla los pesos cambian.
- La tokenización usa `re.findall(r"[a-z0-9]+", ...)`: sin signos `¿` / `?` y sin acentos.
- Los parámetros ya no se copian de `clasificar()`: `predecir()` llama a `extraer_parametros()` con la frase normalizada, así que nunca se mezclan la intención de la red con los parámetros de otra regla.
- Cliente por razón social: `extraer_parametros()` captura el nombre completo (por ejemplo `Acme S.A.`), y `catalogo.clientes_coinciden()` compara normalizando puntuación y acentos y aceptando sufijos legales (`S.A.`, `SRL`, `Ltda.`). Así `cliente="acme"` devuelve la factura de `Acme S.A.` sin confundirla con `Acme Sur`.
- `ajustar()` valida entradas: con frases vacías, longitudes distintas, frases en blanco o etiquetas desconocidas devuelve `None` en vez de lanzar `ValueError`.
- Sin `torch`: `disponible()` es `False` y `predecir()`, `guardar()` y `ajustar()` devuelven `None`. Un `.pt` corrupto, una frase vacía o una frase con tokens desconocidos también devuelven `None` en vez de romper la app.
- `evaluacion/asistente.py` genera las métricas de arriba con `evaluar_asistente(frases=FRASES_VALIDACION, nombre_modelo=..., hoy=...)`: compara la línea base contra la red local; sin modelo devuelve `evaluado=False` y `red_local=None`, y la app sigue andando. `test_evaluacion_asistente.py` cubre 6 casos, incluido el detalle con parámetros y confianza.
- **Pendiente explícito para el PR3 del asistente:** `POST /ml/asistente/consultar` (`app/api/v1/endpoints/ml/asistente.py`, `test_api_asistente.py`, contrato `{"evaluado", "modelo", "resultado"}` y "no entendí" con baja confianza). `app/api/v1/router.py` lo edita solo Moisés: hoy `RUTAS_ML: []` y el OpenAPI sigue en 32 rutas. Este PR es un paso incremental, **no** el cierre del Módulo 4.

### Archivos compartidos, con un solo dueño

| Archivo | Dueño único | Regla |
|---|---|---|
| `app/api/v1/router.py` | Moisés | Registra cada router cuando el módulo esté listo; nadie más lo edita. |
| `app/ml/inferencia/cargador.py` | Joan | Carga modelos y devuelve `None` si no hay. |
| `app/ml/datasets/generar_datos.py` | Andres y Cristian | Cambios por Issue al dueño. |
| `app/core/errors.py` | Antony revisa | Contrato `{"detail", "code"}`. |
| Este README | Cada quien su sección | Cada persona agrega sólo su sección de métricas. |

## 9. Orden de cada módulo

features o reglas → modelos → entrenamiento → evaluación → endpoint → pruebas → README → PR hacia `ml`.
