# ML (paso 0)

Esqueleto nomás. Acá todavía no hay modelos ni lógica de entrenamiento.

## Reglas

- **El ML sugiere, no decide.** La app funciona sin los modelos.
- Si `cargar_modelo(nombre)` no encuentra el archivo en `backend/ml_models/`, devuelve `None`: no se evalúa nada.
- Datos de ejemplo ≠ datos reales. Los de ejemplo van marcados y llevan casos raros inyectados; nunca se mezclan con los reales.
- Modelos entrenados, datos reales/generados y `backend/ml_models/` **no se suben a Git** (ya están ignorados).
- No se importan librerías de ML hasta que los líderes aprueben dependencias nuevas.
- Los routers de `endpoints/ml/` no se registran en `router.py`: los mete el Equipo 4 cuando el módulo esté listo.

## Quién trabaja qué

- `datasets/`, `features/`, `modelos/`, `entrenamiento/`, `inferencia/`: Equipo ML.
- `api/v1/endpoints/ml/`: lo prepara el Equipo ML, lo registra el Equipo 4.
- `tests/ml/`: Equipo ML, con apoyo del Equipo 4 si se prueban rutas.

## Orden de pasos

0. Esqueleto de carpetas y archivos (esta rama, sin lógica).
1. `datasets/generar_datos.py`: facturas y pedidos de EJEMPLO con casos raros.
2. `features/`: rasgos para anomalías, pronóstico y recomendaciones.
3. `modelos/` + `entrenamiento/`: modelos y entrenamiento con datos marcados.
4. `inferencia/` + `endpoints/ml/`: sugerencias; el Equipo 4 registra las rutas.

## Salida de datos

`generar_datos.py` dejará los archivos en `backend/app/ml/datos_generados/` (carpeta ignorada). No crearla a mano todavía.
