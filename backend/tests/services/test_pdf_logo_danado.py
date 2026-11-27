"""Gente: si el logo está dañado, el PDF sale igual y avisa por log."""

import logging
from datetime import date
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from reportlab.platypus.flowables import Flowable

import app.services.pdf as modulo_pdf
from app.services.pdf import construir_datos_comprobante, generar_pdf


@pytest.fixture(autouse=True)
def url_qr_falsa(monkeypatch):
    monkeypatch.setattr(
        modulo_pdf,
        "settings",
        SimpleNamespace(FACTURA_VERIFICACION_BASE_URL="https://verificacion.ejemplo.test"),
    )


def _factura_dict():
    return {
        "numero_serie": "FAC-2026-0009",
        "codigo_verificacion": "ABC123DEF456",
        "fecha": date(2026, 11, 27),
        "cliente_nombre": "Cliente QA",
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


def _png_valido() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (16, 16), (58, 0, 136, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def test_pdf_con_logo_valido(tmp_path):
    archivo = tmp_path / "logo-bueno.png"
    archivo.write_bytes(_png_valido())
    datos = construir_datos_comprobante(
        _factura_dict(),
        configuracion={"empresa_nombre": "Mi Empresa", "logo": str(archivo)},
    )

    assert generar_pdf(datos).startswith(b"%PDF")


def test_pdf_con_logo_corrupto_sale_sin_logo_y_avisaba(tmp_path, caplog):
    archivo = tmp_path / "logo-roto.png"
    # Firma y cabecera bien, pero IDAT cortado: ImageReader lo abre y reportlab
    # revienta al dibujar. Acá lo detectamos antes.
    archivo.write_bytes(_png_valido()[:-25])
    datos = construir_datos_comprobante(
        _factura_dict(),
        configuracion={"empresa_nombre": "Mi Empresa", "logo": str(archivo)},
    )

    with caplog.at_level(logging.WARNING):
        pdf = generar_pdf(datos)

    assert pdf.startswith(b"%PDF")
    assert "Logo ilegible" in caplog.text
    assert str(archivo) not in caplog.text


class _LogoQueFallaAlDibujar(Flowable):
    """Flowable malo a propósito para probar el reintento sin logo."""

    def wrap(self, ancho, alto):
        return (10, 10)

    def draw(self):
        raise RuntimeError("no se puede dibujar")


def test_pdf_reintenta_sin_logo_si_falla_el_dibujo(tmp_path, monkeypatch, caplog):
    archivo = tmp_path / "logo-raro.png"
    archivo.write_bytes(_png_valido())
    monkeypatch.setattr(modulo_pdf, "_cargar_logo", lambda _ruta: _LogoQueFallaAlDibujar())
    datos = construir_datos_comprobante(
        _factura_dict(),
        configuracion={"empresa_nombre": "Mi Empresa", "logo": str(archivo)},
    )

    with caplog.at_level(logging.WARNING):
        pdf = generar_pdf(datos)

    assert pdf.startswith(b"%PDF")
    assert "No se pudo dibujar el logo" in caplog.text
    assert str(archivo) not in caplog.text
