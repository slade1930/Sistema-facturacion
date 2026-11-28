# Semillas del catálogo

Acá cada grupo carga sus productos. El sector **lo da el nombre del archivo**;
no lo escribas dentro de los datos.

| Sector | Archivo que editas | Bloques (meta por persona) |
| --- | --- | --- |
| Supermercado | `supermercado.py` | NIDIA 4, JOSHUA 4, JAVIER 4, ZEUS 4, HUGO 4 |
| Turismo | `turismo.py` | JESUS 4, CRISTHIAN 4, ERICK 4, LUIS_CASTILLO 4, JOSE_RIVERA 4 |
| Tecnología | `tecnologia.py` | MOISES 4, ELIAN 4, IRVING 3, ANTONY 3, MANUEL_VARGAS 3, ANDRES 3 |

## Cómo editar

- Edita **solo tu bloque** del archivo de tu sector. No crees archivos nuevos.
- En `categorias` pones tus categorías con `nombre` y `descripcion`. En
  `productos` pones tus productos. La categoría de cada producto debe estar
  declarada en el mismo archivo.
- Usa nombres de bloque en mayúsculas sin acentos. No escribas `sku`: se genera
  automáticamente con prefijo del sector (`SUP-`, `TUR-` o `TEC-`).
- Los precios y el stock puedes escribirlos como texto (`"12.50"`) o como
  número; siempre se convierten a `Decimal`. Máximo dos decimales.
- Revisa el comentario `EJEMPLO (no cargar)` al final de tu archivo: muestra
  todos los campos que puedes usar.

## Calidad mínima

- Nombres y descripciones propios. No copies nombres ni textos de tiendas ni de
  catálogos de internet. Nada de imágenes de internet: deja `imagen` en `None`
  o usa una ruta local que empiece con `media/`.
- Precios ficticios pero realistas y distintos entre productos. Define
  `precio_unidad`, `unidades_por_caja` y `precio_caja`. Si `permite_media_caja`
  es `true`, define `precio_media_caja` y hazlo menor que `precio_caja`; si es
  `false`, deja `precio_media_caja` en `None`.
- ITBMS: según `docs/tecnica/reglas-de-negocio.md`, el 7 % se aplica solo si el
  producto está gravado. Define `aplica_itbms` explícitamente en **cada**
  producto (`true` o `false`).
- `stock_inicial` razonable, mayor o igual a cero. Solo se aplica al crear el
  producto: volver a cargar no reinicia el stock.
- **Mínimo 3 productos en oferta por grupo**: pon `descuento_pct` mayor que
  cero (entre 0 y 90) en al menos tres de tus productos.
- Usa varias categorías dentro de tu bloque. No repitas nombres de productos
  dentro del sector, aunque estén en bloques distintos o en categorías
  distintas.
- En turismo se vende por **lotes de cupos, noches o entradas**: describe la
  unidad y el lote en `presentacion` y en `descripcion_corta`.
- El archivo completo no debe pasar de 20 productos entre todos los bloques;
  tu bloque no debe pasar de la meta indicada arriba.

## Comandos

Ejecútalos desde la raíz del proyecto, dentro del contenedor de backend. Primero
simula y revisa los errores; después carga de verdad:

```bash
docker compose exec backend python -m app.cli.cargar_catalogo --sector tecnologia --bloque MOISES --simular
docker compose exec backend python -m app.cli.cargar_catalogo --sector tecnologia --bloque MOISES
```

Para cargar el sector completo, quita `--bloque`:

```bash
docker compose exec backend python -m app.cli.cargar_catalogo --sector tecnologia
```

Para ver el avance de todos los sectores y personas (categorías, cargados contra
la meta, ofertas, media caja, reglas incumplidas y total contra 20):

```bash
docker compose exec backend python -m app.cli.verificar_catalogo
```

También puedes filtrar la verificación con `--sector supermercado`, `--sector
turismo` o `--sector tecnologia`.

Si la validación encuentra errores, la carga no escribe nada y la CLI muestra
cada error con el bloque y el índice del producto que hay que corregir.
