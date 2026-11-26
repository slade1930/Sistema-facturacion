"""Pruebas del aporte de Irving para el PDF del comprobante (sin base de datos).

Cubre lo que hoy expone app.services.pdf:
- PDF sin logo: encabezado con datos de empresa (o fallback "(empresa sin
  configurar)") y _cargar_logo() devolviendo None en todos los casos de fallo.
- PDF con logo: imagen válida escalada a máx. 30x18 mm y fallback silencioso
  cuando la ruta no existe, está corrupta o apunta a un directorio.
- Verificación/QR: pdf.py aún NO dibuja QR; lo único que expone hoy es
  datos["codigo_verificacion"] (12 hex) que se imprime como texto en el PDF,
  el preview y el HTML. Estas pruebas fijan ese contrato para que el QR
  futuro (o el endpoint de verificación) consuma el mismo dato sin sorpresas.

No se usa Postgres ni dependencias nuevas: el PNG de prueba se genera con
zlib/struct de la stdlib (PNG RGB 8-bit mínimo).
"""

import struct
import zlib
from datetime import date
from decimal import Decimal

import pytest

from app.services.pdf import (
    _cargar_logo,
    construir_datos_comprobante,
    generar_pdf,
    renderizar_html,
    renderizar_texto,
)
from app.services.verificacion import generar_codigo_verificacion


# ---------------------------------------------------------------------------
# Helpers locales (no se importa test_pdf.py para no acoplar los aportes).
# ---------------------------------------------------------------------------

def _factura_dict(**extra):
    base = {
        "numero_serie": "FAC-2026-0007",
        "codigo_verificacion": "ABC123DEF456",
        "fecha": date(2026, 11, 26),
        "cliente_nombre": "Cliente Irving",
        "cliente_ruc": "8-765-432",
        "mostrar_ruc": True,
        "cliente_direccion": "Vía España, Edif. 2",
        "subtotal": Decimal("100.00"),
        "descuento_total": Decimal("0.00"),
        "base_gravada": Decimal("100.00"),
        "base_exenta": Decimal("0.00"),
        "itbms": Decimal("7.00"),
        "portes": Decimal("0.00"),
        "total": Decimal("107.00"),
        "estado": "emitida",
        "lineas": [
            {
                "orden": 1,
                "descripcion": "Servicio de prueba",
                "cantidad": Decimal("1"),
                "precio_unitario": Decimal("100.00"),
                "descuento_pct": Decimal("0"),
                "gravada": True,
                "monto": Decimal("100.00"),
            }
        ],
    }
    base.update(extra)
    return base


def _png_rgb(ancho: int, alto: int, rgb=(200, 30, 30)) -> bytes:
    """PNG RGB 8-bit mínimo, solo con stdlib (sin Pillow)."""
    def chunk(tipo: bytes, datos: bytes) -> bytes:
        return (
            struct.pack(">I", len(datos))
            + tipo
            + datos
            + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    fila = b"\x00" + bytes(rgb) * ancho  # filtro 0 + píxeles RGB
    idat = zlib.compress(fila * alto)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def _escribir_png(ruta, ancho=600, alto=300):
    ruta.write_bytes(_png_rgb(ancho, alto))
    return str(ruta)


# ---------------------------------------------------------------------------
# PDF sin logo
# ---------------------------------------------------------------------------

class TestPdfSinLogo:
    def test_datos_sin_configuracion_logo_vacio(self):
        d = construir_datos_comprobante(_factura_dict())
        assert d["empresa"]["logo"] == ""
        assert d["empresa"]["nombre"] == ""

    def test_pdf_sin_logo_arranca_con_percent_pdf(self):
        pdf = generar_pdf(_factura_dict())
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 500

    def test_texto_usa_fallback_empresa_sin_configurar(self):
        d = construir_datos_comprobante(_factura_dict())
        texto = renderizar_texto(d)
        assert "(empresa sin configurar)" in texto

    def test_cargar_logo_devuelve_none_sin_ruta(self):
        assert _cargar_logo(None) is None
        assert _cargar_logo("") is None

    def test_cargar_logo_none_cuando_ruta_no_existe(self, tmp_path):
        assert _cargar_logo(str(tmp_path / "no_existe.png")) is None

    def test_cargar_logo_none_cuando_es_directorio(self, tmp_path):
        assert _cargar_logo(str(tmp_path)) is None

    def test_pdf_sin_lineas_no_revienta(self):
        # Edge: factura sin líneas -> totales en cero, tabla solo con cabecera.
        factura = _factura_dict(lineas=[])
        for c in ("subtotal", "descuento_total", "base_gravada",
                  "base_exenta", "itbms", "total"):
            factura[c] = None
        assert generar_pdf(factura).startswith(b"%PDF")


# ---------------------------------------------------------------------------
# PDF con logo
# ---------------------------------------------------------------------------

class TestPdfConLogo:
    def test_cargar_logo_devuelve_flowable_escalado(self, tmp_path):
        from reportlab.lib.units import mm

        ruta = _escribir_png(tmp_path / "logo.png", ancho=600, alto=300)
        logo = _cargar_logo(ruta)

        assert logo is not None
        # reportlab guarda el tamaño escalado en _width/_height (puntos).
        # 600x300 px con tope 30x18 mm: escala por ancho -> 30 mm x 15 mm.
        assert logo._width == pytest.approx(30 * mm, rel=0.01)
        assert logo._height == pytest.approx(15 * mm, rel=0.01)
        assert logo._width <= 30 * mm + 0.01
        assert logo._height <= 18 * mm + 0.01

    def test_cargar_logo_respeta_tope_de_alto(self, tmp_path):
        from reportlab.lib.units import mm

        # Imagen muy alta: manda el alto máximo de 18 mm.
        ruta = _escribir_png(tmp_path / "tall.png", ancho=100, alto=900)
        logo = _cargar_logo(ruta)

        assert logo is not None
        assert logo._height <= 18 * mm + 0.01
        # Mantiene la relación de aspecto 1:9.
        assert logo._width == pytest.approx(logo._height / 9, rel=0.01)

    def test_pdf_con_logo_valido_se_genera(self, tmp_path):
        ruta = _escribir_png(tmp_path / "logo.png")
        d = construir_datos_comprobante(
            _factura_dict(), configuracion={"logo": ruta}
        )
        assert d["empresa"]["logo"] == ruta
        pdf = generar_pdf(d)
        assert pdf.startswith(b"%PDF")

    def test_logo_inexistente_cae_en_silencio(self, tmp_path):
        d = construir_datos_comprobante(
            _factura_dict(),
            configuracion={"empresa_nombre": "Mi Empresa", "logo": "no/existe.png"},
        )
        assert d["empresa"]["logo"] == "no/existe.png"
        assert generar_pdf(d).startswith(b"%PDF")

    def test_logo_corrupto_cae_en_silencio(self, tmp_path):
        falso = tmp_path / "roto.png"
        falso.write_bytes(b"esto no es una imagen PNG")
        assert _cargar_logo(str(falso)) is None
        d = construir_datos_comprobante(_factura_dict(), configuracion={"logo": str(falso)})
        assert generar_pdf(d).startswith(b"%PDF")

    def test_logo_relativo_se_resuelve_desde_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _escribir_png(tmp_path / "logo.png", ancho=200, alto=200)
        logo = _cargar_logo("logo.png")
        assert logo is not None
        # Cuadrada 200x200: escala limitada por el tope menor (18 mm de alto).
        # Ojo: _cargar_logo nunca agranda (escala <= 1.0), por eso 200 px.
        from reportlab.lib.units import mm
        assert logo._height == pytest.approx(18 * mm, rel=0.01)
        assert logo._width == pytest.approx(18 * mm, rel=0.01)

    def test_logo_relativo_inexistente_devuelve_none(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        assert _cargar_logo("no_esta.png") is None


# ---------------------------------------------------------------------------
# Verificación / QR en el PDF
#
# Estado actual (pdf.py @ de1e48b): NO hay QR ni imagen de verificación.
# El comprobante expone datos["codigo_verificacion"] y lo imprime como texto
# en PDF, preview y HTML. Un QR futuro debería codificar ese mismo string
# (o la URL de verificación derivada de él). Estas pruebas fijan el contrato
# que el QR va a consumir, de forma desacoplada de la implementación.
# ---------------------------------------------------------------------------

class TestVerificacionEnComprobante:
    def test_codigo_resolucion_explicito_gana(self, monkeypatch):
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave")
        d = construir_datos_comprobante(
            _factura_dict(codigo_verificacion="PERSISTIDO1"),
            codigo_verificacion="EXPLICITO1",
        )
        assert d["codigo_verificacion"] == "EXPLICITO1"

    def test_codigo_persistido_gana_sobre_hmac(self, monkeypatch):
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave")
        d = construir_datos_comprobante(_factura_dict())
        assert d["codigo_verificacion"] == "ABC123DEF456"

    def test_codigo_generado_por_hmac_cuando_no_hay_otro(self, monkeypatch):
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-de-prueba")
        factura = _factura_dict(codigo_verificacion=None)
        d = construir_datos_comprobante(factura)
        esperado = generar_codigo_verificacion(
            "FAC-2026-0007", Decimal("107.00"), "8-765-432"
        )
        assert d["codigo_verificacion"] == esperado

    def test_sin_clave_ni_codigo_el_error_sube(self, monkeypatch):
        monkeypatch.delenv("FACTURA_HMAC_KEY", raising=False)
        with pytest.raises(RuntimeError, match="FACTURA_HMAC_KEY"):
            construir_datos_comprobante(_factura_dict(codigo_verificacion=None))

    def test_codigo_aparece_en_texto_y_html(self):
        d = construir_datos_comprobante(_factura_dict())
        assert "ABC123DEF456" in renderizar_texto(d)
        assert "ABC123DEF456" in renderizar_html(d)

    def test_pdf_se_genera_con_codigo_explicito_sin_env(self, monkeypatch):
        # Con código explícito no hace falta FACTURA_HMAC_KEY.
        monkeypatch.delenv("FACTURA_HMAC_KEY", raising=False)
        datos = construir_datos_comprobante(
            _factura_dict(codigo_verificacion=None),
            codigo_verificacion="CODIGODE12",
        )
        assert datos["codigo_verificacion"] == "CODIGODE12"
        assert generar_pdf(datos).startswith(b"%PDF")


class TestBaseParaQr:
    """Contrato que consumirá el QR cuando se implemente en pdf.py.

    Hoy el QR NO existe en el PDF; lo que sí existe (y es estable) es
    datos["codigo_verificacion"]. Estas pruebas documentan la forma del dato
    que el QR debe codificar, sin acoplarse a reportlab ni a un endpoint.
    """

    def test_dato_para_qr_es_string_hex_de_12(self, monkeypatch):
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave")
        d = construir_datos_comprobante(_factura_dict(codigo_verificacion=None))
        codigo = d["codigo_verificacion"]
        assert isinstance(codigo, str)
        assert len(codigo) == 12
        assert all(c in "0123456789ABCDEF" for c in codigo)

    def test_codigo_es_determinista_para_el_mismo_comprobante(self, monkeypatch):
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave")
        factura = _factura_dict(codigo_verificacion=None)
        c1 = construir_datos_comprobante(factura)["codigo_verificacion"]
        c2 = construir_datos_comprobante(factura)["codigo_verificacion"]
        assert c1 == c2

    def test_codigo_cambia_si_cambia_el_total(self, monkeypatch):
        monkeypatch.setenv("FACTURA_HMAC_KEY", "clave")
        base = _factura_dict(codigo_verificacion=None)
        otro = _factura_dict(codigo_verificacion=None, total=Decimal("108.00"))
        assert (
            construir_datos_comprobante(base)["codigo_verificacion"]
            != construir_datos_comprobante(otro)["codigo_verificacion"]
        )

    def test_qr_futuro_usara_el_mismo_campo(self):
        # Marcador de contrato: si pdf.py agrega datos["qr"] o similar,
        # este test sigue pasando porque solo exige codigo_verificacion.
        d = construir_datos_comprobante(_factura_dict())
        assert "codigo_verificacion" in d
        assert "numero_serie" in d  # la URL de verificación probablemente lo use
