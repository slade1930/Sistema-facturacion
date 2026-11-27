# ORQUÍDEA — sistema visual de Sistema-facturacion

Fuente de verdad de la interfaz. Si un estilo nuevo en `ui/` no se explica con este documento, hay que cambiar el documento o quitar el estilo.

## Paleta

| Nombre | Hex | Uso | Contraste |
|---|---|---|---|
| Tinta ciruela | `#220A3A` | Texto fuerte, riel lateral | 17,91:1 sobre blanco |
| Violeta orquídea | `#6C2BD9` | Marca y acciones principales | 7,03:1 con blanco |
| Fucsia buganvilla | `#D4157F` | Foco, pestaña activa, sello, atención | 4,98:1 con blanco |
| Fucsia tinta | `#A30F61` | Texto fucsia sobre lila | 6,41:1 sobre lila |
| Lila bruma | `#F1EAFD` | Superficies suaves, filas alternas | 15,29:1 con tinta |
| Blanco pétalo | `#FFFFFF` | Hojas y tickets | fondo de página `#FCFAFF` |
| Éxito | `#145C45` | Estado emitida, confirmaciones | 7,93:1 con blanco |
| Alerta | `#7A4A00` | En revisión | 7,48:1 con blanco |
| Error | `#9C1B2E` | Fallos de validación | 8,05:1 con blanco |
| Anulada | `#6B5F77` | Estado anulada, con tachado | 5,95:1 con blanco |

Contraste calculado con la fórmula WCAG 2.1. **Cambio respecto al encargo:** el fucsia `#D4157F` sobre lila da 4,26:1 y no llega a AA para texto. Se usa `#A30F61` para texto sobre lila; el fucsia original queda reservado a rellenos con texto blanco. Ningún texto usa negro puro.

## Tipografía

- **Bricolage Grotesque** (variable 400–800, licencia OFL): titulares, folios `FAC-AAAA-####` y totales grandes.
- **Onest** (variable 400–700, licencia OFL): texto, etiquetas y datos de tabla.
- Ambas descargadas de Google Fonts, guardadas como `woff2` en `ui/static/fonts/`, con `OFL.txt` al lado. Sin CDN ni peticiones de red al ejecutar.
- Las dos tienen la feature `tnum`. `font-variant-numeric: tabular-nums` en folios, totales y celdas numéricas.
- Escala: `xs` 12/16, `sm` 14/20, `body` 16/24, `h3` 20/28 (600), `h2` 28/34 (700), `h1` 40/46 (800), `folio` 56/58 (800).
- Cuerpo de texto con máximo ~70 caracteres por línea. Jerarquía por tamaño y peso, no por color.

## Espacio, radios y divisores

Escala de espacio: 4, 8, 12, 16, 24, 32, 48, 64. Radios con jerarquía: ticket y esquinas de hoja `2px` (ángulo vivo), tablas `0`, controles `10px`, sello `50%`, paneles `4px`. Un divisor de 1px en lila oscura `#E4D6FA` solo cuando separa bloques reales. Sin sombras grises repetidas.

## Foco y táctil

`:focus-visible` con contorno fucsia de 2px y separación de 2px en todos los controles. Botones, enlaces y campos con área mínima de 44px. El hover de fila marca una barra fucsia a la izquierda; no hay elevación de tarjetas.

## Layout

```
┌──────────────┬────────────────────────────────────────────────┐
│  ∨  pétalo   │  Facturación / Historial                       │
│  Inicio      │  ═══════════════════════════════════════════════  │
│  Nueva       │  Historial de facturas          [Buscar]       │
│ █ Historial █─│  filtros ...                                    │
│  Catálogo    │  ┌ tabla plana, filas lila ───────────────────┐ │
│  Pedidos     │  │ FAC-2026-0007   Cliente       25.00  SELLO │ │
│  Config      │  └────────────────────────────────────────────┘ │
│  Verificar   │                                                │
└──────────────┴────────────────────────────────────────────────┘
     riel ciruela            hoja blanca, ticket troquelado
```

Riel izquierdo en tinta ciruela con la marca y siete enlaces. El ítem activo es una pestaña fucsia que se funde con el área de contenido. Contenido sobre blanco pétalo, ancho máximo 1180px, paddings de 32px. Encabezado con migas cuando aportan, título Bricolage y acción principal a la derecha; pie discreto. Todo el texto a la izquierda; cifras a la derecha. En pantallas medianas el riel se reduce a 76px y muestra etiquetas cortas; en móvil pasa a barra inferior.

## Componentes

`montar_layout` (riel, migas, título, contenedor, pie), `boton_orquidea` (primario, secundario, peligro), `campo_orquidea` (normal, foco, error, deshabilitado), `sello_estado` (emitida, anulada, en revisión), `tabla_orquidea` con paginación, `ticket_factura`, `notificar`, `esqueleto`, `sello_emitir` y `total_animado`.

## Movimiento

1. Una sola entrada por sesión: el riel se despliega y el pétalo se dibuja con trazo; se guarda una marca en `sessionStorage`.
2. El sello: baja, golpea con rebote y rotación leve, y deja marca de tinta al emitir y al verificar una factura válida. Es el momento estrella.
3. Los totales cuentan hacia el nuevo valor en carrito y factura.
4. Botones con presión, avisos que explican qué pasó, esqueletos en lila y transición suave al abrir un detalle.
5. Nada de entradas con fundido y desplazamiento en cada sección. `prefers-reduced-motion` detiene todo. JS propio y mínimo, sin librerías.

## Revisión: ¿esto es lo que haría para cualquier sistema de facturación morado?

No. Cambié cuatro cosas deliberadamente:

- Quité el panel de indicadores genérico. El encabezado muestra el último folio como pie de talonario, no cuatro tarjetas de métricas.
- Los estados dejaron de ser pastillas redondas: son sellos con textura de tinta y rotación; `anulada` va en gris ciruela tachada.
- La tabla no vive dentro de una tarjeta: es una hoja plana con filas lila. El único borde con personalidad es el troquel del ticket.
- El fucsia no decora fondos: aparece solo en foco, pestaña activa, barra de fila y sello. No hay degradado morado-azul, glass ni sombras grises.
