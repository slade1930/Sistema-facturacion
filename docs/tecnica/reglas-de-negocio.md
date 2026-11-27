# Reglas de Negocio

A continuación se detallan las reglas clave que rigen el sistema de facturación (verificadas contra el código de `backend/app/services/`):

*   **Numeración por año:** Las facturas usan el formato **FAC-AAAA-0001** (gestionado por `contador_serie`) y las órdenes de compra **OC-AAAA-0001** (gestionado por `contador_orden_compra`). No se repiten números. El servicio (`serie.py`) usa bloqueos de base de datos (`FOR UPDATE`) para evitar duplicados si dos usuarios facturan al mismo tiempo.
  
*   **ITBMS del 7%:** Se aplica únicamente a las líneas cuyo producto tenga `aplica_itbms = true` (o `gravada = true` en la línea). El cálculo (`totales.py`) separa la base gravada de la exenta y aplica el 7% solo a la gravada.
  
*   **Dinero y Redondeo:** Se usa el tipo de dato `Decimal` con redondeo `ROUND_HALF_UP`. El monto de cada línea se calcula en una sola operación (cantidad × precio con descuento) y se redondea **una sola vez** al final a dos decimales (`NUMERIC(14,2)`).
  
*   **Cálculo por Empaque:** El precio a cobrar depende del campo `cobrar_por`. Si es "caja", se usa el precio de la caja; si es "unidad", se usa el precio unitario. No se hacen divisiones automáticas por las unidades de la caja.
  
*   **Código de Verificación:** Se genera un código de 12 caracteres hexadecimales usando **HMAC-SHA256**. La firma combina el número de serie, el total (redondeado a 2 decimales) y el RUC del cliente. La clave secreta (`FACTURA_HMAC_KEY`) vive en una variable de entorno y **nunca** se sube al repositorio. Si falta la clave, el sistema lanza un error explícito y no permite firmar.
  
*   **Anulación:** Una factura anulada cambia su estado a `ANULADA` y se le llena la `fecha_anulacion`. **Nunca** se borra de la base de datos y conserva su número de serie original (`ciclo_vida.py`). No se puede anular una factura que ya está anulada.
  
*   **Duplicar:** Al duplicar una factura (`ciclo_vida.py`), se crea una nueva con un número de serie nuevo, copiando todas las líneas de la original y recalculando sus totales y su propio código de verificación HMAC.
  
*   **Pedido a factura:** El servicio (`pedidos.py`) convierte un pedido B2B en factura. Valida que el pedido no esté ya facturado ni cancelado, copia los datos del cliente y calcula los totales.
  
*   **Monto en letras:** El sistema convierte el total de la factura a letras en español (ej. *"SON: MIL DOSCIENTOS... CON 56/100"*) usando `numero_a_letras.py`, sin depender de librerías externas.
