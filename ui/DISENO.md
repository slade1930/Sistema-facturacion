# ORQUÍDEA — sistema visual de la facturación

Fuente de verdad de la interfaz. Si un estilo nuevo en `ui/` no se explica con este documento, hay que cambiar el documento o quitar el estilo. La segunda pasada eliminó el riel lateral: la navegación vive arriba.

## Paleta

| Nombre | Hex | Uso | Contraste |
|---|---|---|---|
| Tinta ciruela | `#220A3A` | Texto fuerte, trazo de la marca | 17,91:1 sobre blanco |
| Violeta orquídea | `#6C2BD9` | Acciones principales | 7,03:1 con blanco |
| Fucsia buganvilla | `#D4157F` | Foco, subrayado activo, relleno de sello, atención | 4,98:1 con blanco |
| Fucsia tinta | `#A30F61` | Texto fucsia sobre lila | 6,41:1 sobre lila |
| Lila bruma | `#F1EAFD` | Superficies suaves, filas alternas, cajón | 15,29:1 con tinta |
| Blanco pétalo | `#FFFFFF` | Encabezado, hojas y tickets | fondo de página `#FCFAFF` |
| Éxito | `#145C45` | Estado emitida, confirmaciones | 7,93:1 con blanco |
| Alerta | `#7A4A00` | En revisión | 7,48:1 con blanco |
| Error | `#9C1B2E` | Fallos de validación | 8,05:1 con blanco |
| Anulada | `#6B5F77` | Estado anulada, con tachado | 5,95:1 con blanco |

Contraste calculado con la fórmula WCAG 2.1. El fucsia `#D4157F` sobre lila da 4,26:1 y no llega a AA para texto: se usa `#A30F61` para texto sobre lila; el fucsia original queda reservado a rellenos con texto blanco. Ningún texto usa negro puro.

## Tipografía

- **Bricolage Grotesque** (variable 400–800, OFL): titulares, folios y totales grandes.
- **Onest** (variable 400–700, OFL): texto, etiquetas y datos de tabla.
- Ambas están en `ui/static/fonts/` como `woff2`, con licencia OFL al lado. No hay CDN ni peticiones externas.
- Cifras con `font-variant-numeric: tabular-nums` en folios, totales, importes y celdas numéricas.
- Escala: `xs` 12/16, `sm` 14/20, `body` 16/24, `h3` 20/28, `h2` 28/34, `h1` 40/46, `folio` 56/58.

## Espacio, radios y divisores

Escala de espacio 4, 8, 12, 16, 24, 32, 48, 64. Radios: ticket y hoja `2px`, controles `10px`, cajón y paneles `4px`, tablas `0`, sello `50%`. Un divisor de 1px en lila oscuro `#E4D6FA` solo cuando separa bloques reales. Sin sombras grises repetidas ni degradados decorativos.

## Foco y táctil

`:focus-visible` con contorno fucsia de 2px y separación de 2px. Botones, enlaces y campos con `44px` de alto mínimo. El hover de fila marca una barra fucsia a la izquierda; no hay elevación de tarjetas.

## Navegación superior

```
┌──────────────────────────────────────────────────────────────────────┐
│ ∨ Orquídea · Negocio │ Facturación ▾ Catálogo ▾ Pedidos ▾ … │ Emitir │
├──────────────────────────────────────────────────────────────────────┤
│  Facturas emitidas                                                  │
│  ├──────────────── filtros ordenados ────────────────────────────────┤
│  │ Número      Cliente       Total      Estado                      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

- Encabezado fijo, blanco pétalo. Marca a la izquierda, menú horizontal por tema y acción "Emitir factura" a la derecha.
- El nombre del negocio aparece al lado de la marca **solo si existe en la configuración**; nunca una URL ni una ruta técnica.
- Menús desplegables por tema: Facturación (Talonario, Emitidas), Catálogo (Productos, Carrito), Pedidos (Por facturar, Nuevo pedido), Consultar (Verificación) y Negocio (Datos del negocio). Solo páginas que existen.
- Cada grupo responde a clic, `Enter`/`Espacio` (botón nativo), `ArrowDown` (abre y enfoca el primer enlace) y `Escape` (cierra). Un clic fuera también cierra.
- Activo = subrayado fucsia de 4px y texto tinta ciruela. El subrayado cuelga del enlace hijo correcto, no de un texto decorativo.
- A `≤900px` el menú se convierte en hamburguesa con cajón deslizable desde arriba; se cierra al elegir una opción. No hay barra inferior ni restos del riel.
- Un solo `montar_layout` para las 13 rutas. No hay contenedores paralelos ni estilos de riel residuales.

## Regla de no repetir textos

- Una sola ubicación dice dónde estás: el título descriptivo de la página (`Facturas emitidas`, `Pedidos por facturar`, `Comprobar una factura`). El menú solo nombra la sección (`Emitidas`, `Por facturar`, `Verificación`).
- El título nunca es igual a la opción del menú. Ejemplo: menú `Emitidas` → título `Facturas emitidas`.
- Las migas aparecen solo en páginas de segundo nivel (detalle de factura, detalle/conversión/éxito de pedido, carrito y formulario de pedido) y muestran únicamente el padre. Nunca aparecen en el inicio.
- "Última factura emitida" es dato del inicio; no se repite en el encabezado global.
- No se muestran "NiceGUI", "httpx", "backend", "API", "Interfaz", URLs internas, nombres de archivo ni mensajes de depuración. Solo pueden estar en comentarios o en este documento. Los errores se explican en español con `mostrar_error`.

## Anatomía del inicio

1. **Portada real:** título "Tu facturación, en orden" y ticket troquelado de la última factura emitida (folio, fecha, cliente, RUC, sello, total y enlace al detalle). Si no hay facturas, estado vacío tranquilo.
2. **¿Qué quieres hacer?:** entradas numeradas a módulos que existen: emitir factura, revisar emitidas, armar pedido, ver productos y comprobar factura.
3. **Cómo funciona:** cuatro pasos numerados: pedido → factura → QR → verificación.
4. **Actividad real:** últimas 5 facturas del historial y aviso "Pedidos por facturar: N" solo si el endpoint responde. Sin tarjetas de métricas inventadas. estados de carga, error y vacío.
5. **Verificación pública:** serie y código con el mismo botón "Verificar"; navega a la página de verificación ya precargada.
6. **Pie:** nombre y RUC del negocio solo si existen en la configuración.

## Patrón de formularios

- `seccion_formulario(titulo, ayuda)` con rejilla de 2 columnas en escritorio y 1 en móvil. Etiquetas arriba (`stack-label`), ayuda y errores debajo.
- `campo_orquidea`, `selector_orquidea` (búsqueda para clientes y productos) y `numero_orquidea` (prefijo `$`, alineación derecha, cifras tabulares).
- Foco fucsia, error en tinta de error, deshabilitado con opacidad; ningún estado se define solo por color.
- Barra final pegajosa con acción principal y "Cancelar". El mismo nombre de botón y el mismo aviso de éxito en todo el flujo: "Emitir factura" / "Factura emitida".
- Nueva factura: formulario a la izquierda, ticket resumen en vivo a la derecha (subtotal, descuento, ITBMS y total animado), líneas agregables y quitables. Los cálculos siguen siendo los del backend.

### Configuración del negocio

- Sin fila: se abre el formulario de primera configuración, nunca un error. El primer guardado usa el `PUT` existente con `empresa_nombre` y `empresa_ruc`; después solo se envían los campos cambiados y aparece `Cambios guardados`.
- Los errores de validación se muestran debajo del campo; el logo tiene vista previa y sus fallos se explican sin rutas ni códigos. El nombre y el RUC guardados aparecen en el inicio y en el PDF.
- Si no hay conexión: `No pudimos conectar con el sistema. Revisa tu conexión e inténtalo de nuevo.` con botón `Reintentar`.

### Carrito

- `Añadir al carrito` respeta cantidad y presentación; `Media caja` solo se ofrece si el producto la permite y los inactivos no se pueden añadir. El aviso es `Producto añadido` y la cabecera muestra el contador.
- El carrito vive en el almacenamiento de la pestaña, separado por usuario; las líneas se pueden editar y los totales pasan por esqueleto y se animan con el ticket ORQUÍDEA.
- Estado vacío exacto: `Tu carrito está vacío. Añade productos desde el catálogo`.
- `Confirmar pedido` crea el pedido con el `POST` existente y termina en `Pedido creado`. Los errores 422, 404, 409 y de red se explican con acciones comprensibles, sin códigos.
- Todos los textos usan trato de tú: `Elige`, `Agrega`, `Prueba`, `Revisa`, `Intenta`.

## Tablas y listas

- Tabla plana con filas lila finas, cifras a la derecha, encabezado fijo y paginación con texto claro. Sin tarjeta contenedora.
- En móvil la tabla se convierte en lista apilada con etiqueta y valor por fila; no se pierde información ni hay desplazamiento horizontal.
- Filtros ordenados, nunca una sopa de controles. El estado vacío dice qué hacer, sin repetir el título.

## Componentes

`montar_layout` (encabezado, menú, cajón, título y migas), `boton_orquidea`, `boton_enlace`, `campo_orquidea`, `selector_orquidea`, `numero_orquidea`, `seccion_formulario`, `barra_acciones`, `mostrar_error`, `confirmar_accion`, `esqueleto`, `sello_estado`, `sello_emitir`, `ticket_factura`, `ticket_resumen`, `total_animado`, `tabla_orquidea`, `estado_vacio`, `estado_cargando` y `notificar`.

## Movimiento

1. Una sola entrada por sesión: el encabezado baja y el pétalo se dibuja con trazo; se guarda una marca en `sessionStorage`.
2. El sello: baja, golpea con rebote y rotación leve al emitir y al verificar una factura válida. Es el momento estrella.
3. Los totales cuentan hacia el nuevo valor en el carrito y en el talonario.
4. Botones con presión, avisos que explican qué pasó y esqueletos en lila. No hay entradas por sección ni hovers decorativos.
5. `prefers-reduced-motion` detiene todo. JS propio y mínimo, sin librerías ni peticiones externas.

## Revisión: ¿esto es lo que haría para cualquier sistema de facturación morado?

No. Cambié cuatro cosas deliberadamente:

- Quité el panel de indicadores genérico y el riel: el inicio es un talonario con una sola última factura real, no cuatro tarjetas de métricas.
- Los estados dejaron de ser pastillas redondas: son sellos con textura de tinta y rotación; `anulada` va en gris ciruela tachada.
- La tabla no vive dentro de una tarjeta: es una hoja plana con filas lila. El único borde con personalidad es el troquel del ticket.
- El fucsia no decora fondos: aparece en foco, subrayado activo, barra de fila y sello. No hay degradado morado-azul, glass ni sombras grises.

Autocrítica de la segunda pasada: el borde superior de 6px del ticket y el borde inferior formaban un doble troquel que competía con el sello. Se conserva solo el troquel superior y el inferior se reduce a 1px; la hoja respira y el sello sigue siendo el único golpe visual.
