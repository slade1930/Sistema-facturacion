"""Comprobante de factura para PDF.

FASE ACTUAL (sin dependencias externas en requirements.txt):
- construir_datos_comprobante(): arma el dict estructurado con empresa,
  folio, cliente, líneas, desglose de totales (subtotal, descuento_total,
  base_gravada, base_exenta, itbms 7%, portes, total), total en letras
  (services.numero_a_letras) y código de verificación opcional.
- renderizar_texto(): versión texto plano del comprobante (depuración/preview).
- renderizar_html(): HTML mínimo listo para convertir a PDF cuando los
  líderes aprueben una librería.

DEPENDENCIA PDF PENDIENTE — pedir a los líderes UNA de estas:
- reportlab  -> generación directa de PDF (recomendada, liviana, estable).
- weasyprint -> HTML -> PDF (requiere GTK en Windows, más pesada).
Mientras tanto NADA de este módulo importa esas librerías: los tests
corren sin ellas. Cuando se apruebe, agregar `generar_pdf(datos) -> bytes`
aquí y seguir usando construir_datos_comprobante() como fuente única.

Acepta Factura ORM, dict o cualquier objeto con los atributos del esquema.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, Optional

from app.services.numero_a_letras import monto_a_letras_factura
from app.services.totales import calcular_monto_linea, calcular_totales
from app.utils.formatters import formato_fecha, formato_moneda

# Integración con el código de verificación (HMAC) del equipo de seguridad.
# Si el módulo no existe o falla, el comprobante sale igual con "".
try:
    from app.services.verificacion import (
        generar_codigo_verificacion as _generar_codigo_verificacion,
    )
except Exception:  # pragma: no cover - el módulo puede no estar aún
    _generar_codigo_verificacion = None

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

    La generación HMAC necesita FACTURA_HMAC_KEY en el entorno; si falta
    (o el módulo de verificación no está disponible) devuelve "" sin fallar.
    """
    if explicito:
        return explicito
    guardado = _campo(factura, "codigo_verificacion")
    if guardado:
        return str(guardado)
    if _generar_codigo_verificacion is None:
        return ""
    try:
        return _generar_codigo_verificacion(numero_serie, total, cliente_ruc or "")
    except Exception:
        return ""


def construir_datos_comprobante(
    factura: Any,
    *,
    configuracion: Any = None,
    codigo_verificacion: Optional[str] = None,
    total_en_letras: Optional[str] = None,
) -> dict[str, Any]:
    """Arma el dict único que alimenta texto, HTML y (futuro) PDF binario.

    - configuracion: ConfiguracionNegocio ORM/dict (opcional; si falta, el
      encabezado sale con datos vacíos y el resto del comprobante igual).
    - codigo_verificacion: opcional. Prioridad: este parámetro > el campo
      persistido en la factura > HMAC generado con services.verificacion
      (requiere FACTURA_HMAC_KEY; si falta, queda en "" sin fallar).
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
# Renderizado (sin librerías externas)
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
