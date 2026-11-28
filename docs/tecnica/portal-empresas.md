# Portal de empresas

Decisiones de la etapa A: esqueleto, autenticación, roles, aislamiento, sectores, compra con factura automática e inventario en el backend. Las pantallas completas quedan para las etapas B, C y D.

## Roles

- **empresa**: ve solo lo suyo: catálogo de su sector, carrito, compra con factura automática, sus pedidos, sus facturas (lista, detalle y PDF) y su panel (historial, lo que más pide y recomendaciones de ML). No ve configuración del negocio, inventario ni datos de otras empresas.
- **admin**: ve todo: catálogo completo y su administración, inventario, pedidos, por facturar, empresas, métricas globales y emisión manual de facturas.
- **sistema**: la API-Key válida sin token mantiene el comportamiento actual solo para pruebas y procesos internos. Equivale a admin en esas llamadas.

La regla de oro es que ninguna empresa ve datos ni panel de otra. El aislamiento lo impone el backend desde el token; la interfaz solo muestra lo que el backend devuelve.

## Sectores

Los sectores son `tecnologia`, `turismo` y `supermercado`. Cada categoría y cada empresa tiene un sector. Una empresa solo ve y puede comprar productos de categorías de su sector. Las categorías sin sector son invisibles para las empresas; siguen existiendo para el admin.

## Registro y contraseñas

El registro pide nombre, RUC, dirección, teléfono, correo, sucursal, contraseña y sector. El login usa nombre de la empresa y contraseña. El nombre se normaliza sin espacios sobrantes y en minúsculas; nombre y RUC deben ser únicos.

La contraseña tiene entre 8 y 64 caracteres, con al menos una mayúscula y al menos un número. No hay contraseñas por defecto en el repositorio. El hash usa PBKDF2-HMAC-SHA256 con sal aleatoria y comparación segura.

## Sesiones

El token se genera con la librería estándar y en la base solo se guarda su sha256. La sesión caduca por inactividad a los 30 minutos y de forma absoluta a las 12 horas. Se revoca al cerrar sesión, al cambiar la contraseña en las demás sesiones y al desactivar la cuenta.

El límite de intentos es de 5 fallos en 15 minutos, con bloqueo de 30 minutos, por IP y por nombre. La cabecera `X-Forwarded-For` solo se acepta cuando la petición trae una API-Key válida; el límite es por proceso.

## Compra con factura automática

La empresa elige productos, confirma y en una sola operación se crean el pedido y la factura: totales, ITBMS, número `FAC-AAAA-0001`, código de verificación y PDF. Quien emite es nuestro negocio (`configuracion_negocio`) a nombre de la empresa. No hay emisores múltiples ni series por empresa.

Se reutilizan los servicios existentes de pedidos, totales, serie, verificación, PDF y ciclo de vida. No se reimplementan esos cálculos ni cambian sus firmas públicas. Una clave de idempotencia evita facturas duplicadas por doble clic.

## Inventario

Las existencias se guardan en unidades base por producto. Un producto sin fila de inventario no tiene control de stock: se puede comprar y no se descuenta. El ajuste lo hace el admin y registra un movimiento. La devolución de stock al anular una factura queda pendiente para la etapa D; no se toca `ciclo_vida.py` en esta etapa.

## Administrador

El primer administrador se crea con la CLI del backend. La contraseña se toma de la variable de entorno `ADMIN_PASSWORD` o de `getpass`, nunca como argumento. La cuenta queda marcada para cambiar la clave al primer acceso.

## Etapas pendientes

- **Etapa B**: pantallas de autenticación y del portal de la empresa, incluido su panel.
- **Etapa C**: pantallas de administración (empresas, catálogo, inventario, pedidos y auditoría).
- **Etapa D**: devolución de stock al anular facturas y cierre del portal.
