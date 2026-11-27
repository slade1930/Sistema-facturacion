# backend/tests/services/test_pdf_qr_joshua.py
"""Pruebas extra de PDF con logo y verificación QR (Joshua). Sin base de datos."""
import struct
import zlib
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.services.pdf as pdf_mod
from app.services.pdf import (
    _cargar_logo,
    construir_datos_comprobante,
    generar_pdf,
    renderizar_html,
)
from app.services.verificacion import (
    generar_codigo_verificacion,
    validar_codigo_verificacion,
)

CLAVE_PRUEBA = "clave-de-prueba-joshua"


@pytest.fixture(autouse=True)
def configuracion_de_prueba(monkeypatch):
    """Configuración falsa para todas las pruebas: no toca la base de datos ni el .env real."""
    stub = SimpleNamespace(
        FACTURA_VERIFICACION_BASE_URL="https://verificacion.ejemplo.test",
        FACTURA_HMAC_KEY=CLAVE_PRUEBA,
    )
    monkeypatch.setattr(pdf_mod, "settings", stub)
    monkeypatch.setenv("FACTURA_HMAC_KEY", CLAVE_PRUEBA)


def _factura(**extra):
    base = {
        "numero_serie": "FAC-2026-0100",
        "codigo_verificacion": None,
        "fecha": date(2026, 11, 26),
        "cliente_nombre": "Cliente Prueba",
        "cliente_ruc": "8-000-111",
        "mostrar_ruc": True,
        "subtotal": Decimal("50.00"),
        "descuento_total": Decimal("0.00"),
        "base_gravada": Decimal("50.00"),
        "base_exenta": Decimal("0.00"),
        "itbms": Decimal("3.50"),
        "portes": Decimal("0.00"),
        "total": Decimal("53.50"),
        "estado": "emitida",
        "lineas": [{
            "orden": 1,
            "descripcion": "Producto de prueba",
            "cantidad": Decimal("1"),
            "precio_unitario": Decimal("50.00"),
            "descuento_pct": Decimal("0"),
            "gravada": True,
            "monto": Decimal("50.00"),
        }],
    }
    base.update(extra)
    return base


def _png_bytes(ancho=40, alto=20):
    """Genera un PNG válido en memoria, sin depender de base64."""
    fila = b"\x00" + b"\xff\x00\x00" * ancho
    raw = fila * alto

    def bloque(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(raw))
            + bloque(b"IEND", b""))


def _logo(tmp_path, nombre="logo.png"):
    ruta = tmp_path / nombre
    ruta.write_bytes(_png_bytes())
    return str(ruta)


def _datos():
    return construir_datos_comprobante(
        _factura(), configuracion=None,
        codigo_verificacion="a1b2c3d4e5f6",
        total_en_letras="Cincuenta y tres balboas con 50/100",
    )


# ---------- Logo ----------

def test_cargar_logo_ruta_vacia_devuelve_none():
    assert _cargar_logo("") is None


def test_cargar_logo_archivo_inexistente_devuelve_none(tmp_path):
    assert _cargar_logo(str(tmp_path / "no_existe.png")) is None


def test_cargar_logo_png_valido_devuelve_algo(tmp_path):
    assert _cargar_logo(_logo(tmp_path)) is not None


# ---------- PDF ----------

def test_pdf_sin_logo_es_un_pdf_valido():
    pdf = generar_pdf(_datos())
    assert pdf[:5] == b"%PDF-"


def test_pdf_termina_correctamente():
    pdf = generar_pdf(_datos())
    assert pdf.rstrip().endswith(b"%%EOF")


# ---------- Código de verificación ----------

def test_codigo_aparece_en_html():
    codigo = "a1b2c3d4e5f6"
    datos = construir_datos_comprobante(
        _factura(), configuracion=None,
        codigo_verificacion=codigo,
        total_en_letras="Cincuenta y tres balboas con 50/100",
    )
    assert codigo in renderizar_html(datos)


def test_codigo_es_determinista_y_de_12_caracteres():
    a = generar_codigo_verificacion("FAC-2026-0100", Decimal("53.50"), "8-000-111")
    b = generar_codigo_verificacion("FAC-2026-0100", Decimal("53.50"), "8-000-111")
    assert len(a) == 12
    assert a == b


def test_codigo_cambia_si_cambia_el_total():
    a = generar_codigo_verificacion("FAC-2026-0100", Decimal("53.50"), "8-000-111")
    b = generar_codigo_verificacion("FAC-2026-0100", Decimal("60.00"), "8-000-111")
    assert a != b


def test_codigo_alterado_no_se_valida():
    codigo = generar_codigo_verificacion("FAC-2026-0100", Decimal("53.50"), "8-000-111")
    otro = "0" * 12 if codigo != "0" * 12 else "1" * 12
    assert validar_codigo_verificacion("FAC-2026-0100", otro, Decimal("53.50")) is False
