# Base de Datos y Esquema

El sistema usa PostgreSQL con 10 tablas y 7 relaciones.

## Tablas y Relaciones
1. **Configuración:** `configuracion_negocio`, `contador_serie`, `contador_orden_compra`. (Sin FK entre ellas ni con factura).
2. **Facturación:** `factura`, `linea_factura` (Relación 1 a N).
3. **Catálogo:** `categoria`, `producto` (Relación 1 a N).
4. **Pedidos B2B:** `cliente_b2b`, `pedido_b2b`, `linea_pedido_b2b`. (El campo `factura_generada_id` NO tiene UNIQUE).

## Detalle de Campos (Principales)
*   **configuracion_negocio:** id, nombre, ruc, direccion, telefono, correo, logo_url, notas.
*   **contador_serie:** anio, ultimo_numero.
*   **contador_orden_compra:** anio, ultimo_numero.
*   **factura:** id, numero_serie, codigo_verificacion, datos del cliente, subtotal, itbms, total, estado, fecha_anulacion, base_gravada, base_exenta.
*   **linea_factura:** id, factura_id (FK), producto_id (FK), cantidad, precio_unitario, descuento, subtotal, gravada.
*   **categoria:** id, nombre.
*   **producto:** id, categoria_id (FK), nombre, sku, precio_caja, precio_media_caja, precio_unidad, aplica_itbms.
*   **cliente_b2b:** id, nombre_empresa, ruc, condicion_pago.
*   **pedido_b2b:** id, cliente_id (FK), factura_generada_id (FK, sin UNIQUE), estado, total_estimado.
*   **linea_pedido_b2b:** id, pedido_id (FK), producto_id (FK), tipo_empaque, cantidad, subtotal.

## Los 5 ENUM
*(Nota: Valores pendientes por confirmar con el código del Equipo 1)*
*   `condicion_pago`: Pendiente
*   `estado` (factura): Pendiente
*   `estado` (pedido): Pendiente
*   `cobrar_por`: Pendiente
*   `tipo_empaque`: Pendiente

## Migraciones
El proyecto usa Alembic. Actualmente existen **dos migraciones** en `backend/alembic/versions/`. Solo el Equipo 1 crea nuevas migraciones.
