# Reglas de Negocio

A continuación se detallan las reglas clave que rigen el sistema de facturación:

* **Numeración por año:** Las facturas usan el formato **FAC-AAAA-0001** (gestionado por `contador_serie`) y las órdenes de compra **OC-AAAA-0001** (gestionado por `contador_orden_compra`). No se repiten números.
* **ITBMS del 7%:** Se aplica únicamente a las líneas cuyo producto tenga `aplica_itbms = true`. La factura guarda base gravada, base exenta, ITBMS y total.
* **Dinero y Redondeo:** Se usa el tipo de dato `Decimal` con redondeo `ROUND_HALF_UP` y se guarda como `NUMERIC(14,2)`. Solo se hace un redondeo al final.
* **Código de Verificación:** Se genera un código de 12 caracteres usando HMAC-SHA256. La clave secreta vive en una variable de entorno.
* **Anulación:** Una factura anulada cambia su estado y se le llena la `fecha_anulacion`. **Nunca** se borra de la base de datos.
* **Duplicar:** Al duplicar una factura, se crea una nueva con un número nuevo, copiando todas las líneas de la original.
