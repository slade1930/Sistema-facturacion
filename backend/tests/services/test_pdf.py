"""Pruebas unitarias de app.services.pdf (sin librerías PDF ni base de datos).

pdf.py en esta fase construye datos estructurados y renderiza texto/HTML;
no genera binario .pdf hasta que los líderes aprueben la dependencia.
"""

from datetime import date
from decimal import Decimal

from app.services.pdf import (
    construir_datos_comprobante,
    renderizar_html,
    renderizar_texto,
)


def _factura_dict(**extra):
    base = {
        "numero_serie": "FAC-2026-0001",
        "codigo_verificacion": "ABC123DEF456",
        "fecha": date(2026, 11, 24),
        "cliente_nombre": "Cliente Prueba",
        "cliente_ruc": "8-123-456",
        "mostrar_ruc": True,
        "cliente_direccion": "Calle 1",
        "subtotal": Decimal("20.00"),
        "descuento_total": Decimal("0.00"),
        "base_gravada": Decimal("20.00"),
        "base_exenta": Decimal("0.00"),
        "itbms": Decimal("1.40"),
        "portes": Decimal("0.00"),
        "total": Decimal("21.40"),
        "estado": "emitida",
        "lineas": [
            {
                "orden": 1,
                "descripcion": "Producto A",
                "cantidad": Decimal("2"),
                "precio_unitario": Decimal("10.00"),
                "descuento_pct": Decimal("0"),
                "gravada": True,
                "monto": Decimal("20.00"),
            }
        ],
    }
    base.update(extra)
    return base


class TestConstruirDatosComprobante:
    def test_usa_totales_guardados(self):
        d = construir_datos_comprobante(_factura_dict())
        assert d["numero_serie"] == "FAC-2026-0001"
        assert d["totales"]["total"] == Decimal("21.40")
        assert d["totales"]["itbms"] == Decimal("1.40")
        assert d["totales_fmt"]["total"] == "21.40"

    def test_total_en_letras_automatico(self):
        d = construir_datos_comprobante(_factura_dict())
        assert d["total_en_letras"].startswith("SON:")
        assert "CON 40/100" in d["total_en_letras"]

    def test_total_en_letras_parametro_opcional(self):
        d = construir_datos_comprobante(
            _factura_dict(), total_en_letras="SON: VEINTIUN CON 40/100"
        )
        assert d["total_en_letras"] == "SON: VEINTIUN CON 40/100"

    def test_codigo_verificacion_como_parametro(self):
        # El HMAC aún no existe: se puede inyectar sin romper nada.
        d = construir_datos_comprobante(
            _factura_dict(codigo_verificacion=None),
            codigo_verificacion="HMAC12345678",
        )
        assert d["codigo_verificacion"] == "HMAC12345678"

    def test_sin_configuracion_no_revienta(self):
        d = construir_datos_comprobante(_factura_dict())
        assert d["empresa"]["nombre"] == ""

    def test_con_configuracion_dict(self):
        d = construir_datos_comprobante(
            _factura_dict(),
            configuracion={"empresa_nombre": "Mi Empresa", "empresa_ruc": "155"},
        )
        assert d["empresa"]["nombre"] == "Mi Empresa"
        assert d["empresa"]["ruc"] == "155"

    def test_recalcula_totales_si_faltan(self):
        # Si la factura solo trae líneas, pdf.py usa services.totales:
        # ITBMS 7% solo sobre la línea gravada.
        factura = _factura_dict()
        for c in ("subtotal", "descuento_total", "base_gravada",
                  "base_exenta", "itbms", "total"):
            factura[c] = None
        factura["lineas"] = [
            {
                "orden": 1, "descripcion": "G", "cantidad": Decimal("1"),
                "precio_unitario": Decimal("100.00"), "descuento_pct": Decimal("0"),
                "gravada": True, "monto": Decimal("100.00"),
            },
            {
                "orden": 2, "descripcion": "E", "cantidad": Decimal("1"),
                "precio_unitario": Decimal("50.00"), "descuento_pct": Decimal("0"),
                "gravada": False, "monto": Decimal("50.00"),
            },
        ]
        d = construir_datos_comprobante(factura)
        assert d["totales"]["itbms"] == Decimal("7.00")  # solo la gravada
        assert d["totales"]["total"] == Decimal("157.00")

    def test_monto_linea_sin_persistir_se_calcula(self):
        factura = _factura_dict()
        factura["lineas"][0]["monto"] = None
        d = construir_datos_comprobante(factura)
        assert d["lineas"][0]["monto_fmt"] == "20.00"

    def test_sin_hmac_key_el_codigo_queda_vacio_sin_fallar(self, monkeypatch):
        # FACTURA_HMAC_KEY ausente: el comprobante se arma igual.
        monkeypatch.delenv("FACTURA_HMAC_KEY", raising=False)
        factura = _factura_dict(codigo_verificacion=None)
        d = construir_datos_comprobante(factura)
        assert d["codigo_verificacion"] == ""

    def test_con_hmac_key_genera_codigo_automatico(self, monkeypatch):
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")
        factura = _factura_dict(codigo_verificacion=None)
        d = construir_datos_comprobante(factura)
        assert len(d["codigo_verificacion"]) == 12
        assert all(c in "0123456789ABCDEF" for c in d["codigo_verificacion"])

    def test_codigo_persistido_gana_sobre_hmac(self, monkeypatch):
        # Si la factura ya tiene código guardado, no se regenera.
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")
        d = construir_datos_comprobante(_factura_dict())
        assert d["codigo_verificacion"] == "ABC123DEF456"

    def test_enums_salen_por_value_no_por_nombre(self):
        from app.models.facturacion import CondicionPago, EstadoFactura

        d = construir_datos_comprobante(
            _factura_dict(
                condicion_pago=CondicionPago.CONTADO,
                estado=EstadoFactura.EMITIDA,
            )
        )
        assert d["condicion_pago"] == "contado"
        assert d["estado"] == "emitida"


class TestRenderizar:
    def test_texto_contiene_datos_clave(self):
        d = construir_datos_comprobante(_factura_dict())
        texto = renderizar_texto(d)
        assert "FAC-2026-0001" in texto
        assert "ABC123DEF456" in texto
        assert "Cliente Prueba" in texto
        assert "ITBMS (7%)" in texto
        assert "21.40" in texto
        assert "SON:" in texto

    def test_html_es_documento_valido_basico(self):
        d = construir_datos_comprobante(_factura_dict())
        html = renderizar_html(d)
        assert html.startswith("<!DOCTYPE html>")
        assert "<title>Factura FAC-2026-0001</title>" in html
        assert "ITBMS (7%)" in html
        assert "Producto A" in html
