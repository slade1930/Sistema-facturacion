# Esquema de Base de Datos

El sistema utiliza PostgreSQL. El esquema oficial consta de 10 tablas y 7 relaciones. Puedes ver el diagrama visual completo en los archivos `esquema_facturacion_estilo_final.drawio` y `.png` subidos en esta misma carpeta.

## Bloques de Tablas y Relaciones

1. **Configuración y contadores:**
   - `configuracion_negocio`: Datos de la empresa.
   - `contador_serie`: Lleva el control de los números de factura por año.
   - `contador_orden_compra`: Lleva el control de los números de orden de compra.
   *(Nota: Estas tablas no tienen llaves foráneas (FK) entre sí ni con la tabla factura).*

2. **Facturación:**
   - `factura`: Cabecera de la factura (totales, estado, fecha).
   - `linea_factura`: Detalle de los productos facturados.
   *(Relación: factura 1 -> N linea_factura).*

3. **Catálogo:**
   - `categoria`: Agrupación de productos.
   - `producto`: Ítems disponibles (precio por caja, media caja y unidad).
   *(Relación: categoria 1 -> N producto; producto 1 -> N linea_factura y linea_pedido_b2b).*

4. **Pedidos B2B:**
   - `cliente_b2b`: Clientes comerciales.
   - `pedido_b2b`: Cabecera del pedido. *(Nota: el campo `factura_generada_id` apunta a la factura creada y NO tiene restricción UNIQUE, tal como estaba en el sistema original).*
   - `linea_pedido_b2b`: Detalle del pedido.
   *(Relación: cliente 1 -> N pedido; pedido 1 -> N línea; factura 0..1 -> N pedido).*

## Los 5 ENUM del sistema

La base de datos usa tipos ENUM para evitar errores en los estados. Los valores exactos son:

* `condicion_pago`: [Preguntar al Equipo 1].
* `estado` (de factura): [Preguntar al Equipo 1].
* `estado` (de pedido): [Preguntar al Equipo 1].
* `cobrar_por`: [Preguntar al Equipo 1 ].
* `tipo_empaque`: [Preguntar al Equipo 1 ].

## Migraciones con Alembic

Las tablas y sus cambios se manejan con Alembic. Actualmente, el proyecto cuenta con dos (2) migraciones registradas en la carpeta `backend/alembic/versions/`. Solo el equipo de base de datos (Equipo 1) tiene permitido crear nuevas migraciones para evitar conflictos.
