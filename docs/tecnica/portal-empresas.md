# Portal de empresas

Decisiones consolidadas al cierre de la etapa D: autenticación, roles, aislamiento, sectores, compra con factura automática e inventario en el backend (etapa A), portal de la empresa (etapa B), administración (etapa C) y endurecimiento con devolución de stock y cobertura punta a punta (etapa D).

## Roles

- **empresa**: ve solo lo suyo: catálogo de su sector, carrito, compra con factura automática, sus pedidos, sus facturas (lista, detalle y PDF) y su panel (historial, lo que más pide y recomendaciones de ML). No ve configuración del negocio, inventario ni datos de otras empresas.
- **admin**: ve todo: catálogo completo y su administración, inventario, pedidos, por facturar, empresas, métricas globales y emisión manual de facturas.
- **sistema**: la API-Key válida sin token mantiene el comportamiento actual solo para pruebas y procesos internos. Equivale a admin en esas llamadas.

La regla de oro es que ninguna empresa ve datos ni panel de otra. El aislamiento lo impone el backend desde el token; la interfaz solo muestra lo que el backend devuelve.

En la API, un token de empresa filtra categorías y productos por sector, clientes, pedidos, facturas, historial y PDF por `cliente_id`. Un recurso ajeno responde 404. Cuando el cuerpo o la query contradicen al cliente del token, la respuesta es 403. Configuración, altas de catálogo y clientes, facturación manual, anulación, duplicación, listado de por facturar, facturación de pedidos y ML salvo recomendaciones responden 403 para empresa. Las recomendaciones de empresa usan solo sus pedidos y facturas y productos de su sector. `/verificar` sigue público porque valida un comprobante con número y código.

## Matriz de roles y acceso

| Rol | Ve | No ve |
| --- | --- | --- |
| **empresa** | Su catálogo por sector, carrito, compra, pedidos, facturas y PDF propios, su cuenta y su panel. | Datos de otra empresa, inventario, administración, auditoría ni configuración del negocio. |
| **admin** | Todo el catálogo, empresas, inventario, pedidos, por facturar, auditoría, métricas globales y emisión manual. | No necesita el portal de empresa: entra por `/admin`. |
| **sistema** (API-Key sin token) | Las operaciones internas y de prueba permitidas por el backend. | No tiene sesión de portal: no usa las rutas `/portal/**` ni `/admin/**`. |
| **anónimo** | `/`, `/catalogo`, `/carrito`, `/verificar`, `/login` y `/registro`. | Cualquier ruta del portal o de administración: vuelve a `/login`. |

| Ruta | Regla de acceso |
| --- | --- |
| `/`, `/catalogo`, `/carrito`, `/verificar`, `/login`, `/registro` | Públicas. `/verificar` comprueba serie y código sin sesión. |
| `/empresa` | Entrada al portal: exige sesión de empresa activa; si no hay sesión, redirige a `/login`. |
| `/portal/inicio`, `/portal/catalogo`, `/portal/carrito`, `/portal/compra-exitosa`, `/portal/pedidos`, `/portal/facturas`, `/portal/mi-cuenta`, `/portal/cambiar-clave` | Sesión de empresa activa (`auth.exigir_sesion()`). El backend filtra todo por el `cliente_id` del token. |
| `/portal/factura-detalle` | Lo anterior y, además, la factura debe pertenecer al `cliente_id` del token; si no, responde 404. |
| `/admin`, `/admin/panel`, `/admin/empresas`, `/admin/catalogo`, `/admin/catalogo/categorias`, `/admin/inventario`, `/admin/pedidos`, `/admin/pedidos/por-facturar`, `/admin/auditoria` | Sesión de administrador (`components.admin.seguridad.exigir_admin()`). Una empresa o un anónimo vuelve a `/login`. |
| `/facturacion/**`, `/pedidos/**` | Flujo interno previo: sigue usando la API-Key y las reglas del backend, sin sesión de portal. |

La redirección es una decisión de la interfaz; el aislamiento real lo vuelve a comprobar el backend en cada llamada. Una empresa suspendida no obtiene sesión y una sesión expirada vuelve al login.

## Sectores

Los sectores son `tecnologia`, `turismo` y `supermercado`. Cada categoría y cada empresa tiene un sector. Una empresa solo ve y puede comprar productos de categorías de su sector. Las categorías sin sector son invisibles para las empresas; siguen existiendo para el admin. El sector se envía en `sector` al crear o editar categorías y clientes; en el registro de empresa es obligatorio.

## Registro y contraseñas

El registro pide nombre, RUC, dirección, teléfono, correo, sucursal, contraseña y sector. El login usa nombre de la empresa y contraseña. El nombre se normaliza sin espacios sobrantes y en minúsculas; nombre y RUC deben ser únicos.

La contraseña tiene entre 8 y 64 caracteres, con al menos una mayúscula y al menos un número. No hay contraseñas por defecto en el repositorio. El hash usa PBKDF2-HMAC-SHA256 con sal aleatoria y comparación segura.

## Sesiones

El token se genera con la librería estándar y en la base solo se guarda su sha256. La sesión caduca por inactividad a los 30 minutos y de forma absoluta a las 12 horas. Se revoca al cerrar sesión, al cambiar la contraseña en las demás sesiones y al desactivar la cuenta.

El límite de intentos es de 5 fallos en 15 minutos, con bloqueo de 30 minutos, por IP y por nombre. La cabecera `X-Forwarded-For` solo se acepta cuando la petición trae una API-Key válida; el límite es por proceso.

Cada inicio de sesión llama a `limpiar_sesiones_vencidas`: borra las sesiones expiradas o revocadas con más de siete días de antigüedad, como máximo una vez por hora y por proceso, dentro de la transacción del login. La interfaz conserva el token en el almacenamiento de la pestaña; si la sesión expiró, el portal vuelve a `/login` en lugar de mostrar datos viejos.

## Compra con factura automática

La empresa elige productos, confirma y en una sola operación se crean el pedido y la factura: totales, ITBMS, número `FAC-AAAA-0001`, código de verificación y PDF. Quien emite es nuestro negocio (`configuracion_negocio`) a nombre de la empresa. No hay emisores múltiples ni series por empresa.

El flujo completo es: registro o login, catálogo filtrado por sector, carrito con presentación y cantidad, `POST /api/v1/compras`, pantalla de compra exitosa con el número de factura y, desde `/portal/facturas`, detalle y descarga del PDF. Si el stock no alcanza, la respuesta es un error y no se crean pedido, factura ni movimientos.

Se reutilizan los servicios existentes de pedidos, totales, serie, verificación, PDF y ciclo de vida. No se reimplementan esos cálculos ni cambian sus firmas públicas. `POST /api/v1/compras` confirma en una sola transacción pedido, factura y descuento de inventario; usa `LineaPedido` y `facturar_pedido_b2b` del servicio de pedidos. Una clave de idempotencia por empresa evita facturas duplicadas por doble clic: repetir la clave devuelve la misma factura con `reutilizada=true`. La factura queda ligada al cliente del pedido mediante `cliente_id`; el backfill de la migración usó el pedido ligado y, si no lo había, un RUC exacto y único.

El stock se bloquea con `SELECT ... FOR UPDATE` ordenado por `producto_id`. La conversión acordada es `caja = cantidad × unidades_por_caja`, `unidad = cantidad` y `media_caja = cantidad × unidades_por_caja / 2`, con `Decimal` y sin redondear. Cada salida registra un `MovimientoInventario` con `factura_id`. Los productos sin fila de inventario no tienen control de stock. `PUT /api/v1/admin/inventario/{id}` ajusta existencias; `GET /api/v1/admin/inventario` y `GET /api/v1/admin/inventario/{id}/movimientos` son globales. `GET /api/v1/admin/resumen` da métricas globales solo para admin o sistema. La devolución de stock al anular factura ya está incluida en la etapa D y se detalla en Inventario.

Para descontar inventario se usa la conversión acordada: caja = cantidad × `unidades_por_caja`; unidad = cantidad; media caja = cantidad × `unidades_por_caja` / 2, con `Decimal` y sin redondear. Esta conversión es solo para existencias; los precios y totales siguen las reglas ya existentes y no dividen entre `unidades_por_caja`.

## Inventario

Las existencias se guardan en unidades base por producto. Un producto sin fila de inventario no tiene control de stock: se puede comprar y no se descuenta. El ajuste lo hace el admin y registra un movimiento.

Al anular una factura, el endpoint llama a `devolver_por_factura` después de marcarla como anulada y antes del `commit`: repone las salidas ligadas a esa factura solo para productos con fila de inventario, genera entradas de anulación y es idempotente. Una anulación repetida o una factura sin movimientos propios no cambia el stock; las facturas duplicadas no descuentan existencias, por eso tampoco reponen.

## Administrador

El primer administrador se crea con la CLI del backend:

```bash
docker compose exec backend python -m app.cli.crear_admin --usuario nombre-elegido
```

La contraseña se toma de la variable de entorno `ADMIN_PASSWORD` o de `getpass`, nunca como argumento ni como valor fijo en el repositorio. La cuenta queda marcada para cambiar la clave al primer acceso. `ADMIN_PASSWORD` debe agregarse a `.env.example`; esta etapa no edita ese archivo.

## Variables nuevas del cierre

| Variable | Componente | Uso |
| --- | --- | --- |
| `CORS_ORIGINS` | API | Orígenes explícitos separados por comas (esquema, host y puerto). El comodín `*` se ignora; solo se responden preflights y cabeceras de origen para orígenes listados. |
| `UI_STORAGE_SECRET` | Interfaz | Secreto propio del almacenamiento de la pestaña. Es obligatorio fuera de las pruebas y nunca se deriva de la API-Key del backend. |

Todas las respuestas de la API llevan cabeceras de seguridad; las rutas de autenticación se marcan `no-store` y los errores de validación ya no devuelven el valor enviado. La revisión del esquema OpenAPI exige que cada operación tenga declarada su regla de acceso (pública, autenticación, empresa, administrador, API-Key o ML) y la comprueba sin credenciales.

## Estado del cierre

- **Etapa A**: backend del portal, roles, aislamiento, sectores, compra con factura automática e inventario.
- **Etapa B**: autenticación, registro, portal de la empresa, carrito, facturas y panel propio.
- **Etapa C**: panel de administración de empresas, catálogo, inventario, pedidos y auditoría.
- **Etapa D**: endurecimiento de cabeceras y secretos, devolución de stock al anular y pruebas de punta a punta.
