"""Pruebas de la interfaz de catálogo con marca, presentación y ofertas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components.shared import en_oferta, precio_con_descuento
from pages.admin.catalogo import _filas_productos


def test_precio_con_descuento_usa_redondeo_comercial():
    assert precio_con_descuento("10.00", "15") == "8.50"
    assert precio_con_descuento("1.25", 0) == "1.25"
    assert precio_con_descuento("3.33", "15") == "2.83"


def test_en_oferta_solo_con_descuento_positivo():
    assert en_oferta({"descuento_pct": "15.00"})
    assert not en_oferta({"descuento_pct": "0.00"})
    assert not en_oferta({})


def test_filas_admin_muestran_etiquetas_y_precio_descontado():
    filas = _filas_productos(
        [
            {
                "id": 1,
                "nombre": "Producto de prueba",
                "marca": "Marca propia",
                "presentacion": "paquete",
                "descuento_pct": "15.00",
                "precio_caja": "10.00",
                "precio_unidad": "1.25",
                "sector": "tecnologia",
                "estado_activo": True,
            }
        ]
    )

    assert filas[0]["marca"] == "Marca propia"
    assert filas[0]["presentacion"] == "paquete"
    assert filas[0]["oferta"] == "15.00 %"
    assert filas[0]["precio_caja_oferta"] == "8.50"
    assert filas[0]["precio_unidad_oferta"] == "1.06"
