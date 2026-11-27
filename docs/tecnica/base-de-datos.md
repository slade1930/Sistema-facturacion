# Base de Datos y Esquema

El sistema usa PostgreSQL con 10 tablas y 7 relaciones, modeladas con SQLAlchemy.

## Tablas y Relaciones
1. **Configuración y contadores:** `configuracion_negocio`, `contador_serie`, `contador_orden_compra`. 
   *(Nota: No tienen llaves foráneas (FK) entre sí ni con la tabla factura).*
2. **Facturación:** `factura`, `linea_factura` (Relación 1 a N).
3. **Catálogo:** `categoria`, `producto` (Relación 1 a N).
4. **Pedidos B2B:** `cliente_b2b`, `pedido_b2b`, `linea_pedido_b2b`. 
   *(Nota: el campo `factura_generada_id` NO tiene restricción UNIQUE).*

## Los 5 ENUM (Valores exactos extraídos del código)
*   `condicion_pago`: `contado`, `credito`
*   `estado` (de factura): `emitida`, `anulada`, `en_revision`
*   `estado` (de pedido): `pendiente`, `procesando`, `facturado`, `cancelado`
*   `cobrar_por`: `unidad`, `caja`
*   `tipo_empaque`: `caja`, `media_caja`, `unidad`

## Detalle de Campos (Principales)
*   **configuracion_negocio:** id, empresa_nombre, empresa_ruc, mostrar_ruc, empresa_direccion, empresa_correo, empresa_telefono, logo, color_principal, color_barra_factura, color_tabla, datos_bancarios, notas_predeterminadas, actualizado.
*   **contador_serie:** id, anio, ultimo_numero.
*   **contador_orden_compra:** id, anio, ultimo_numero.
*   **factura:** id, numero_serie, codigo_verificacion, fecha, cliente_nombre, cliente_ruc, mostrar_ruc, cliente_direccion, cliente_telefono, cliente_correo, sucursal, vendedor, orden_compra, condicion_pago, portes, notas, subtotal, descuento_total, base_gravada, base_exenta, itbms, total, estado, en_revision, puntaje_anomalia, motivo_anomalia, fecha_creacion, fecha_anulacion.
*   **linea_factura:** id, factura_id, orden, descripcion, codigo_barras, categoria, cantidad, precio_unitario, precio_unidad, descuento_pct, gravada, unidades_por_caja, cobrar_por, monto, producto_id.
*   **categoria:** id, nombre.
*   **producto:** id, categoria_id, nombre, sku, codigo_barras, descripcion_corta, imagen, precio_caja, precio_media_caja, permite_media_caja, precio_unidad, precio_consumidor, unidades_por_caja, aplica_itbms, estado_activo, fecha_creacion, fecha_actualizacion.
*   **cliente_b2b:** id, nombre_empresa, ruc, email_contacto, telefono, direccion, fecha_registro, activo.
*   **pedido_b2b:** id, cliente_id, estado, total_estimado, notas, factura_generada_id, fecha_creacion, fecha_actualizacion.
*   **linea_pedido_b2b:** id, pedido_id, producto_id, tipo_empaque, cantidad, subtotal, orden.

## Migraciones
El proyecto usa Alembic. Actualmente existen **tres migraciones** en `backend/alembic/versions/`: `0001_inicial.py`, `0002_correcciones_fidelidad_original.py` y `0003_anomalias_factura.py`. La `0003` agrega `en_revision`, `puntaje_anomalia` y `motivo_anomalia` en `factura`. Solo el Equipo 1 crea nuevas migraciones.
