# Documentación de Endpoints (API)

La API está construida con FastAPI y organizada en módulos dentro de `backend/app/api/v1/endpoints/`. Todos los endpoints requieren autenticación (`requiere_auth`) excepto el de verificación pública.

## 1. Módulo de Catálogo (`/catalogo`)
Archivos ubicados en `endpoints/catalogo/`:

*   **`api.py`**: Endpoints generales del módulo.
*   **`catalogo.py`**: CRUD de Categorías, Productos y Clientes B2B. Permite listar, crear, actualizar y desactivar (borrado lógico).
*   **`carrito.py`**: Endpoint `POST /carrito/calcular` que recibe los productos, calcula subtotales con la presentación (caja/unidad) y devuelve los totales con ITBMS.
*   **`pedidos_b2b.py`**: Creación de pedidos B2B (`POST /pedidos`) y consulta de un pedido específico (`GET /pedidos/{pedido_id}`).

## 2. Módulo de Facturación (`/facturacion`)
Archivos ubicados en `endpoints/facturacion/`:

*   **`facturas.py`**: 
    *   `POST /facturas`: Crea una factura, genera el número de serie, aplica los totales (ITBMS) y el código de verificación HMAC.
    *   `GET /facturas/{factura_id}`: Consulta una factura.
    *   `POST /facturas/{factura_id}/anular`: Anula la factura (cambio de estado).
    *   `POST /facturas/{factura_id}/duplicar`: Duplica la factura con un nuevo número.
*   **`historial.py`**: `GET /historial` para listar facturas con filtros (estado, fechas, cliente) y paginación.
*   **`configuracion.py`**: `GET`, `PUT` y `POST /logo` para la configuración del negocio (colores, logo, datos bancarios).
*   **`pdf.py`**: `GET /facturas/{factura_id}/pdf` para generar y descargar el PDF de la factura.
*   **`pedidos.py`**: 
    *   `GET /pedidos`: Lista pedidos con paginación.
    *   `GET /pedidos/por-facturar`: Lista pedidos pendientes que no tienen factura.
    *   `POST /pedidos/{pedido_id}/facturar`: Convierte un pedido B2B en factura.
*   **`verificar.py`**: `GET /verificar/{numero_serie}/{codigo}` (Endpoint público) que valida el código HMAC de la factura.

## 3. Módulo de Machine Learning (`/ml`)
**Estado: En construcción.**
El Equipo de ML preparó los esqueletos de las rutas, pero la lógica aún no está conectada al `router.py` principal. Los archivos creados son:
*   **`anomalias.py`**: Ruta `/ml/anomalias` (detección de anomalías).
*   **`asistente.py`**: Ruta `/ml/asistente` (asistente inteligente).
*   **`pronostico.py`**: Ruta `/ml/pronostico` (pronóstico de ventas).
*   **`recomendaciones.py`**: Ruta `/ml/recomendaciones` (recomendaciones).
