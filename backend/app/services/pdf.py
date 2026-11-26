"""Gente, acá armamos el comprobante de la factura y su PDF.

- construir_datos_comprobante(): arma el dict estructurado con empresa,
  folio, cliente, líneas, desglose de totales, total en letras y código de
  verificación. Es la fuente única para el texto, el HTML y el PDF.
- renderizar_texto(): texto plano para preview y logs.
- renderizar_html(): HTML mínimo del comprobante.
- generar_pdf(): el binario PDF, con reportlab, sin dependencias nuevas.

El código de verificación se usa tal cual si la factura ya lo trae. Si hay
que generarlo, se llama a services.verificacion y cualquier fallo (por
ejemplo, que falte FACTURA_HMAC_KEY) se deja subir: nada de dejarlo en "".

Acepta Factura ORM, dict o cualquier objeto con los atributos del esquema.
"""

from datetime import date, datetime
from decimal import Decimal
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.numero_a_letras import monto_a_letras_factura
from app.services.totales import calcular_monto_linea, calcular_totales
from app.services.verificacion import (
    generar_codigo_verificacion as _generar_codigo_verificacion,
)
from app.utils.formatters import formato_fecha, formato_moneda

_CAMPOS_TOTALES = (
    "subtotal",
    "descuento_total",
    "base_gravada",
    "base_exenta",
    "itbms",
    "total",
)


def _campo(fuente: Any, nombre: str, defecto: Any = None) -> Any:
    if isinstance(fuente, Mapping):
        return fuente.get(nombre, defecto)
    return getattr(fuente, nombre, defecto)


def _normalizar_linea(linea: Any) -> dict[str, Any]:
    return {
        "orden": _campo(linea, "orden"),
        "descripcion": _campo(linea, "descripcion", "") or "",
        "cantidad": _campo(linea, "cantidad", Decimal("0")),
        "precio_unitario": _campo(linea, "precio_unitario", Decimal("0")),
        "descuento_pct": _campo(linea, "descuento_pct", Decimal("0")),
        "gravada": bool(_campo(linea, "gravada", True)),
        "monto": _campo(linea, "monto"),
    }


def _totales_de(factura: Any, lineas: list[dict[str, Any]]) -> dict[str, Decimal]:
    """Usa los campos guardados en la factura; si faltan, recalcula.

    Recalcular con services.totales garantiza la regla ITBMS 7% solo en
    líneas gravadas aunque la factura aún no tenga los totales persistidos.
    """
    guardados = {c: _campo(factura, c) for c in _CAMPOS_TOTALES}
    if all(v is not None for v in guardados.values()):
        return {c: Decimal(str(v)) for c, v in guardados.items()}
    return calcular_totales(lineas, _campo(factura, "portes", Decimal("0.00")))


def _valor_enum(valor: Any) -> str:
    """Enums del esquema se guardan por .value ('contado', no 'CondicionPago.CONTADO')."""
    return str(getattr(valor, "value", valor) or "")


def _resolver_codigo_verificacion(
    factura: Any,
    numero_serie: str,
    total: Decimal,
    cliente_ruc: str,
    explicito: Optional[str],
) -> str:
    """Prioridad: parámetro explícito > campo persistido > HMAC generado.

    La generación HMAC necesita FACTURA_HMAC_KEY en el entorno. Si falla,
    el error se propaga: acá no disfrazamos el problema con un código vacío.
    """
    if explicito:
        return explicito
    guardado = _campo(factura, "codigo_verificacion")
    if guardado:
        return str(guardado)
    return _generar_codigo_verificacion(numero_serie, total, cliente_ruc or "")


def construir_datos_comprobante(
    factura: Any,
    *,
    configuracion: Any = None,
    codigo_verificacion: Optional[str] = None,
    total_en_letras: Optional[str] = None,
) -> dict[str, Any]:
    """Arma el dict único que alimenta texto, HTML y PDF binario.

    - configuracion: ConfiguracionNegocio ORM/dict (opcional; si falta, el
      encabezado sale con datos vacíos y el resto del comprobante igual).
    - codigo_verificacion: opcional. Prioridad: este parámetro > el campo
      persistido en la factura > HMAC generado con services.verificacion
      (requiere FACTURA_HMAC_KEY; si falla, el error sube).
    - total_en_letras: igual, opcional; por defecto se calcula con
      services.numero_a_letras.
    """
    lineas_raw = _campo(factura, "lineas", []) or []
    lineas = [_normalizar_linea(l) for l in lineas_raw]
    totales = _totales_de(factura, lineas)

    if total_en_letras is None:
        total_en_letras = monto_a_letras_factura(totales["total"])

    def cfg(campo: str, defecto: Any = "") -> Any:
        return _campo(configuracion, campo, defecto) if configuracion else defecto

    fecha = _campo(factura, "fecha")
    fecha_creacion = _campo(factura, "fecha_creacion")
    numero_serie = _campo(factura, "numero_serie", "")
    codigo_verificacion_resuelto = _resolver_codigo_verificacion(
        factura,
        numero_serie,
        totales["total"],
        _campo(factura, "cliente_ruc") or "",
        codigo_verificacion,
    )

    return {
        "empresa": {
            "nombre": cfg("empresa_nombre"),
            "ruc": cfg("empresa_ruc"),
            "direccion": cfg("empresa_direccion"),
            "correo": cfg("empresa_correo"),
            "telefono": cfg("empresa_telefono"),
            "logo": cfg("logo"),
        },
        "numero_serie": numero_serie,
        "codigo_verificacion": codigo_verificacion_resuelto,
        "fecha": formato_fecha(fecha),
        "fecha_creacion": (
            formato_fecha(fecha_creacion)
            if isinstance(fecha_creacion, (date, datetime))
            else str(fecha_creacion or "")
        ),
        "cliente": {
            "nombre": _campo(factura, "cliente_nombre", ""),
            "ruc": _campo(factura, "cliente_ruc") or "",
            "direccion": _campo(factura, "cliente_direccion") or "",
            "telefono": _campo(factura, "cliente_telefono") or "",
            "correo": _campo(factura, "cliente_correo") or "",
            "mostrar_ruc": bool(_campo(factura, "mostrar_ruc", True)),
        },
        "sucursal": _campo(factura, "sucursal") or "",
        "vendedor": _campo(factura, "vendedor") or "",
        "orden_compra": _campo(factura, "orden_compra") or "",
        "condicion_pago": _valor_enum(_campo(factura, "condicion_pago", "")),
        "notas": _campo(factura, "notas") or "",
        "lineas": [
            {
                **l,
                "cantidad_fmt": formato_moneda(l["cantidad"]),
                "precio_fmt": formato_moneda(l["precio_unitario"]),
                "monto_fmt": formato_moneda(
                    l["monto"] if l["monto"] is not None else calcular_monto_linea(l)
                ),
            }
            for l in lineas
        ],
        "totales": {c: totales[c] for c in _CAMPOS_TOTALES},
        "totales_fmt": {
            c: formato_moneda(totales[c]) for c in _CAMPOS_TOTALES
        },
        "portes_fmt": formato_moneda(_campo(factura, "portes", Decimal("0"))),
        "total_en_letras": total_en_letras,
        "estado": _valor_enum(_campo(factura, "estado", "")),
    }


# ---------------------------------------------------------------------------
# Renderizado: texto, HTML y PDF
# ---------------------------------------------------------------------------

def renderizar_texto(datos: dict[str, Any]) -> str:
    """Comprobante en texto plano, una línea por campo. Para preview/logs."""
    e = datos["empresa"]
    c = datos["cliente"]
    out = [
        "=" * 60,
        f"FACTURA {datos['numero_serie']}",
        f"Código de verificación: {datos['codigo_verificacion']}",
        f"Fecha: {datos['fecha']}    Estado: {datos['estado']}",
        "-" * 60,
        e["nombre"] or "(empresa sin configurar)",
    ]
    if e["ruc"]:
        out.append(f"RUC: {e['ruc']}")
    if e["direccion"]:
        out.append(e["direccion"])
    out += [
        "-" * 60,
        f"Cliente: {c['nombre']}",
    ]
    if c["ruc"] and c["mostrar_ruc"]:
        out.append(f"RUC cliente: {c['ruc']}")
    if c["direccion"]:
        out.append(c["direccion"])
    out += ["-" * 60, f"{'#':>3} {'Descripción':<34} {'Cant.':>8} {'Monto':>12}", "-" * 60]
    for l in datos["lineas"]:
        out.append(
            f"{l['orden'] or 0:>3} {l['descripcion'][:34]:<34} "
            f"{l['cantidad_fmt']:>8} {l['monto_fmt']:>12}"
        )
    out += [
        "-" * 60,
        f"Subtotal:            {datos['totales_fmt']['subtotal']:>12}",
        f"Descuento:           {datos['totales_fmt']['descuento_total']:>12}",
        f"Base gravada:        {datos['totales_fmt']['base_gravada']:>12}",
        f"Base exenta:         {datos['totales_fmt']['base_exenta']:>12}",
        f"ITBMS (7%):          {datos['totales_fmt']['itbms']:>12}",
        f"Portes:              {datos['portes_fmt']:>12}",
        "=" * 60,
        f"TOTAL:               {datos['totales_fmt']['total']:>12}",
        "=" * 60,
        datos["total_en_letras"],
        "=" * 60,
    ]
    return "\n".join(out)


def renderizar_html(datos: dict[str, Any]) -> str:
    """HTML mínimo del comprobante.

    Cuando se apruebe weasyprint (o similar), este HTML se convierte a PDF
    sin tocar construir_datos_comprobante().
    """
    e = datos["empresa"]
    c = datos["cliente"]
    filas = "".join(
        "<tr>"
        f"<td>{l['orden'] or ''}</td><td>{l['descripcion']}</td>"
        f"<td class='num'>{l['cantidad_fmt']}</td>"
        f"<td class='num'>{l['precio_fmt']}</td>"
        f"<td class='num'>{l['monto_fmt']}</td>"
        "</tr>"
        for l in datos["lineas"]
    )
    t = datos["totales_fmt"]
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Factura {datos['numero_serie']}</title>
<style>
body {{ font-family: Arial, sans-serif; font-size: 12px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #999; padding: 4px 6px; }}
.num {{ text-align: right; }}
.total {{ font-weight: bold; font-size: 14px; }}
</style></head><body>
<h2>{e['nombre'] or 'Factura'}</h2>
<p>RUC: {e['ruc']}<br>{e['direccion'] or ''}<br>{e['correo'] or ''} {e['telefono'] or ''}</p>
<hr>
<p><b>Factura:</b> {datos['numero_serie']} &nbsp; <b>Fecha:</b> {datos['fecha']}<br>
<b>Verificación:</b> {datos['codigo_verificacion']} &nbsp; <b>Estado:</b> {datos['estado']}<br>
<b>Cliente:</b> {c['nombre']} {c['ruc'] if c['mostrar_ruc'] else ''}<br>
{c['direccion'] or ''}</p>
<table>
<tr><th>#</th><th>Descripción</th><th class="num">Cantidad</th><th class="num">Precio</th><th class="num">Monto</th></tr>
{filas}
</table>
<table>
<tr><td>Subtotal</td><td class="num">{t['subtotal']}</td></tr>
<tr><td>Descuento</td><td class="num">{t['descuento_total']}</td></tr>
<tr><td>Base gravada</td><td class="num">{t['base_gravada']}</td></tr>
<tr><td>Base exenta</td><td class="num">{t['base_exenta']}</td></tr>
<tr><td>ITBMS (7%)</td><td class="num">{t['itbms']}</td></tr>
<tr><td>Portes</td><td class="num">{datos['portes_fmt']}</td></tr>
<tr class="total"><td>TOTAL</td><td class="num">{t['total']}</td></tr>
</table>
<p><b>{datos['total_en_letras']}</b></p>
</body></html>"""


def _cargar_logo(ruta_logo: Any) -> Optional[Any]:
    """Devuelve el Flowable Image del logo o None si no se puede usar.

    El campo ConfiguracionNegocio.logo guarda una ruta (absoluta o relativa
    al cwd / backend). Acá nunca lanzamos: si el logo falta, no existe o la
    imagen está corrupta, el PDF sale exactamente igual que sin logo.
    """
    if not ruta_logo:
        return None
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Image as Imagen
    except ImportError:
        return None
    try:
        ruta = Path(str(ruta_logo)).expanduser()
        if not ruta.is_absolute():
            base_backend = Path(__file__).resolve().parents[2]
            candidatos = [ruta, Path.cwd() / ruta, base_backend / ruta]
            ruta = next((c for c in candidatos if c.is_file()), candidatos[0])
        if not ruta.is_file():
            return None
        lector = ImageReader(str(ruta))
        ancho_px, alto_px = lector.getSize()
        if ancho_px <= 0 or alto_px <= 0:
            return None
        max_ancho, max_alto = 30 * mm, 18 * mm
        escala = min(max_ancho / ancho_px, max_alto / alto_px, 1.0)
        return Imagen(str(ruta), width=ancho_px * escala, height=alto_px * escala)
    except Exception:
        return None


def generar_pdf(datos: dict[str, Any]) -> bytes:
    """Gente, devuelve la factura en PDF listo para guardar o enviar.

    Si le pasamos la factura directo, primero armamos el dict con
    construir_datos_comprobante(). Todo lo que dibuja sale de ese dict.
    """
    if not isinstance(datos, Mapping) or "empresa" not in datos:
        datos = construir_datos_comprobante(datos)

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Factura {datos['numero_serie']}",
    )
    estilos = getSampleStyleSheet()
    normal = estilos["Normal"]
    normal.fontSize = 9
    normal.leading = 12

    def texto(valor: Any) -> Paragraph:
        return Paragraph(escape(str(valor or "")), normal)

    empresa = datos["empresa"]
    cliente = datos["cliente"]
    totales = datos["totales_fmt"]

    historia = [
        Paragraph(f"FACTURA {escape(str(datos['numero_serie']))}", estilos["Title"]),
        Spacer(1, 4 * mm),
    ]

    encabezado_empresa = [texto(empresa["nombre"] or "(empresa sin configurar)")]
    if empresa["ruc"]:
        encabezado_empresa.append(texto(f"RUC: {empresa['ruc']}"))
    if empresa["direccion"]:
        encabezado_empresa.append(texto(empresa["direccion"]))
    if empresa["correo"] or empresa["telefono"]:
        encabezado_empresa.append(texto(f"{empresa['correo']} {empresa['telefono']}".strip()))

    logo = _cargar_logo(empresa.get("logo"))
    if logo is not None:
        ancho_disponible = letter[0] - (18 + 18) * mm
        tabla_encabezado = Table(
            [[logo, encabezado_empresa]],
            colWidths=[32 * mm, ancho_disponible - 32 * mm],
        )
        tabla_encabezado.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        historia.append(tabla_encabezado)
    else:
        historia += encabezado_empresa

    historia += [
        Spacer(1, 3 * mm),
        texto(
            f"Fecha: {datos['fecha']} | Estado: {datos['estado']} | "
            f"Verificación: {datos['codigo_verificacion']}"
        ),
        texto(
            f"Cliente: {cliente['nombre']}"
            + (f" | RUC: {cliente['ruc']}" if cliente["ruc"] and cliente["mostrar_ruc"] else "")
        ),
    ]
    if cliente["direccion"]:
        historia.append(texto(f"Dirección: {cliente['direccion']}"))
    if cliente["telefono"] or cliente["correo"]:
        historia.append(texto(f"Teléfono: {cliente['telefono']} | Correo: {cliente['correo']}"))
    historia.append(Spacer(1, 4 * mm))

    filas = [["#", "Descripción", "Cant.", "Precio", "Monto"]]
    for linea in datos["lineas"]:
        filas.append([
            str(linea["orden"] or ""),
            linea["descripcion"],
            linea["cantidad_fmt"],
            linea["precio_fmt"],
            linea["monto_fmt"],
        ])
    tabla = Table(
        filas,
        colWidths=[10 * mm, 90 * mm, 22 * mm, 24 * mm, 26 * mm],
        repeatRows=1,
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    historia += [tabla, Spacer(1, 4 * mm)]

    resumen = [
        ["Subtotal", totales["subtotal"]],
        ["Descuento", totales["descuento_total"]],
        ["Base gravada", totales["base_gravada"]],
        ["Base exenta", totales["base_exenta"]],
        ["ITBMS (7%)", totales["itbms"]],
        ["Portes", datos["portes_fmt"]],
        ["TOTAL", totales["total"]],
    ]
    tabla_totales = Table(resumen, colWidths=[45 * mm, 30 * mm], hAlign="RIGHT")
    tabla_totales.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    historia += [
        tabla_totales,
        Spacer(1, 4 * mm),
        Paragraph(escape(datos["total_en_letras"]), estilos["Heading2"]),
        texto(f"Código de verificación: {datos['codigo_verificacion']}"),
    ]
    if datos["notas"]:
        historia += [Spacer(1, 2 * mm), texto(f"Notas: {datos['notas']}")]

    documento.build(historia)
    return buffer.getvalue()
