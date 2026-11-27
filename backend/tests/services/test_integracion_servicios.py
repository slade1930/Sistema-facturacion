"""Prueba integral de los servicios del Equipo 2 (sin base de datos real).

Encadena los módulos en el orden en que los usa el flujo de facturación:
validadores -> totales -> series -> verificación -> comprobante -> ciclo de vida.
Solo usa dicts/objetos en memoria y sqlite en memoria cuando haga falta ORM.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.models.facturacion import EstadoFactura, Factura
from app.services.ciclo_vida import FacturaYaAnuladaError, anular_factura
from app.services.numero_a_letras import monto_a_letras_factura
from app.services.pdf import (
    construir_datos_comprobante,
    renderizar_html,
    renderizar_texto,
)
from app.services.totales import aplicar_totales
from app.services.verificacion import (
    generar_codigo_verificacion,
    validar_codigo_verificacion,
)
from app.utils.validators import (
    es_serie_factura_valida,
    extraer_anio,
    validar_lineas,
)


def _linea(**kwargs):
    """Línea como dict con los campos del esquema oficial."""
    base = {
        "orden": 1,
        "descripcion": "Producto de prueba",
        "cantidad": Decimal("1"),
        "precio_unitario": Decimal("10.00"),
        "descuento_pct": Decimal("0.00"),
        "gravada": True,
        "unidades_por_caja": 1,
        "cobrar_por": "unidad",
        "monto": None,
    }
    base.update(kwargs)
    return base


def _factura_dict() -> dict:
    """Factura mixta: línea gravada con descuento, exenta y gravada a $0."""
    return {
        "numero_serie": "FAC-2026-0007",
        "codigo_verificacion": "",
        "fecha": date(2026, 11, 24),
        "cliente_nombre": "Cliente Integración",
        "cliente_ruc": "155596713-2-2020",
        "mostrar_ruc": True,
        "cliente_direccion": "Ciudad de Panamá",
        "cliente_telefono": "",
        "cliente_correo": "",
        "sucursal": "Matriz",
        "vendedor": "Vendedor 1",
        "orden_compra": "",
        "condicion_pago": "contado",
        "portes": Decimal("5.00"),
        "notas": "",
        "estado": EstadoFactura.EMITIDA,
        "lineas": [
            _linea(
                orden=1,
                descripcion="Arroz 5lb",
                cantidad=Decimal("2"),
                precio_unitario=Decimal("1.005"),  # bruto 2.01 HALF_UP
                descuento_pct=Decimal("10.00"),
                gravada=True,
            ),
            _linea(
                orden=2,
                descripcion="Exento de ITBMS",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("20.00"),
                gravada=False,
            ),
            _linea(
                orden=3,
                descripcion="Muestra gratis",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("0.00"),
                gravada=True,
            ),
        ],
    }


def test_flujo_completo_emision_a_comprobante(monkeypatch):
    monkeypatch.setenv("FACTURA_HMAC_KEY", "clave-integracion")
    factura = _factura_dict()

    # 1) Validadores aceptan las líneas del esquema.
    validar_lineas(factura["lineas"])

    # 2) Totales: ITBMS 7% solo sobre la base gravada.
    #    L1: bruto 2.01, dto 0.20 -> 1.81 gravada.
    #    L2: 20.00 exenta. L3: 0.00 gravada. Portes 5.00 sin ITBMS.
    totales = aplicar_totales(factura)
    assert factura["lineas"][0]["monto"] == Decimal("1.81")
    assert totales == {
        # Con descuentos el subtotal es el bruto (2.01 + 20.00), dto aparte.
        "subtotal": Decimal("22.01"),
        "descuento_total": Decimal("0.20"),
        "base_gravada": Decimal("1.81"),
        "base_exenta": Decimal("20.00"),
        "itbms": Decimal("0.13"),  # 1.81 * 0.07 = 0.1267 -> 0.13
        "total": Decimal("26.94"),
    }
    assert factura["total"] == totales["total"]

    # 3) Folio con formato oficial.
    assert es_serie_factura_valida(factura["numero_serie"])
    assert extraer_anio(factura["numero_serie"]) == 2026

    # 4) Código de verificación HMAC: se genera y se valida.
    codigo = generar_codigo_verificacion(
        factura["numero_serie"], totales["total"], factura["cliente_ruc"]
    )
    factura["codigo_verificacion"] = codigo
    assert len(codigo) == 12
    assert validar_codigo_verificacion(
        codigo,
        factura["numero_serie"],
        totales["total"],
        factura["cliente_ruc"],
    )
    assert not validar_codigo_verificacion(
        codigo,
        factura["numero_serie"],
        totales["total"] + Decimal("0.01"),
        factura["cliente_ruc"],
    )

    # 5) Comprobante: usa los totales persistidos y el código guardado.
    configuracion = {
        "empresa_nombre": "Distribuidora Prueba",
        "empresa_ruc": "155596713-2-2020",
        "empresa_direccion": "Vía España, Panamá",
        "empresa_correo": "ventas@prueba.pa",
        "empresa_telefono": "300-0000",
    }
    datos = construir_datos_comprobante(factura, configuracion=configuracion)
    assert datos["numero_serie"] == "FAC-2026-0007"
    assert datos["codigo_verificacion"] == codigo
    assert datos["totales"]["total"] == Decimal("26.94")
    assert datos["totales_fmt"]["itbms"] == "0.13"
    assert datos["total_en_letras"] == monto_a_letras_factura(Decimal("26.94"))
    assert datos["estado"] == "emitida"
    assert len(datos["lineas"]) == 3

    # 6) Renderizado texto y HTML reflejan el mismo comprobante.
    texto = renderizar_texto(datos)
    assert "FACTURA FAC-2026-0007" in texto
    assert codigo in texto
    assert "TOTAL:" in texto
    html = renderizar_html(datos)
    assert "<!DOCTYPE html>" in html
    assert "FAC-2026-0007" in html
    assert codigo in html


def test_anulacion_deja_comprobante_en_estado_anulada():
    factura_orm = Factura(
        numero_serie="FAC-2026-0007",
        codigo_verificacion="CODIGO123456",
        fecha=date(2026, 11, 24),
        cliente_nombre="Cliente Integración",
        cliente_ruc="155596713-2-2020",
        estado=EstadoFactura.EMITIDA,
        portes=Decimal("0.00"),
    )

    anular_factura(factura_orm)

    assert factura_orm.estado is EstadoFactura.ANULADA
    datos = construir_datos_comprobante(factura_orm)
    assert datos["estado"] == "anulada"

    with pytest.raises(FacturaYaAnuladaError):
        anular_factura(factura_orm)


def test_linea_invalida_detiene_el_flujo_antes_de_calcular():
    factura = _factura_dict()
    factura["lineas"][1]["cantidad"] = Decimal("0.001")  # < 0.01

    with pytest.raises(ValueError, match="Línea 2"):
        validar_lineas(factura["lineas"])
