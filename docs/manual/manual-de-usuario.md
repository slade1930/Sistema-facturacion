# Manual de Usuario

La interfaz propia ya está disponible en http://localhost:8080 (NiceGUI). Desde ahí se usan facturas, historial, catálogo, pedidos, configuración y verificación. Para probar endpoints directamente podés usar Swagger UI en http://localhost:8000/docs.

Las rutas `/api/v1` piden la cabecera `X-API-Key` con el valor definido en `.env`. `/health` y `/api/v1/verificar/{numero_serie}/{codigo}` son públicas.

## Facturas

1. `POST /api/v1/facturas` crea la factura y devuelve su `id`, `numero_serie` y `codigo_verificacion`.
2. `GET /api/v1/facturas/{factura_id}/pdf` descarga el PDF con logo y QR.
3. `POST /api/v1/facturas/{factura_id}/duplicar` genera otra factura a partir de una existente.
4. `POST /api/v1/facturas/{factura_id}/anular` la anula sin borrarla.
5. `GET /api/v1/historial` lista las facturas.

## Verificación

El QR de la factura apunta a `GET /api/v1/verificar/{numero_serie}/{codigo}`. Si devuelve `"valida": true`, la factura es auténtica.

## Catálogo y configuración

- `GET /api/v1/productos` y `GET /api/v1/categorias`: consultar el catálogo; `GET /api/v1/catalogo/buscar`: buscar productos.
- Altas y cambios: `POST`/`PUT` en `/api/v1/productos` y `/api/v1/categorias`. Las bajas lógicas son `DELETE /api/v1/productos/{producto_id}`.
- `GET`/`PUT /api/v1/configuracion`: datos de la empresa; `POST /api/v1/configuracion/logo`: subir el logo del PDF.

## Pedidos B2B

- `POST /api/v1/pedidos` crea el pedido.
- `GET /api/v1/pedidos/por-facturar` lista los pendientes.
- `POST /api/v1/pedidos/{pedido_id}/facturar` genera la factura del pedido.
