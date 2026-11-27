"""Pruebas de features/pronostico.py con datos generados en tmp_path."""
import pytest

from app.ml.datasets import generar_datos as gd
from app.ml.features import pronostico as feat


def _datos(tmp_path, n=250):
    dataset = gd.construir_dataset(n_facturas=n, n_pedidos=0, semilla=gd.SEMILLA)
    gd.escribir_csvs(dataset, tmp_path)
    return gd.cargar_dataset_ml(tmp_path)


def test_ventas_mensuales_total_solo_emitidas(tmp_path):
    datos = _datos(tmp_path)
    regs = feat.ventas_mensuales(datos["facturas"], nivel="total")
    assert regs and all(r["clave"] == "total" for r in regs)
    periodos = [r["periodo"] for r in regs]
    assert periodos == sorted(periodos)
    esperado = sum(
        float(f["total"]) for f in datos["facturas"]
        if f["estado"] != "anulada"
    )
    assert abs(sum(r["total"] for r in regs) - round(esperado, 2)) < 1.0


def test_ventas_mensuales_por_producto_y_categoria(tmp_path):
    datos = _datos(tmp_path)
    prod = feat.ventas_mensuales(
        datos["facturas"], datos["lineas_factura"], nivel="producto"
    )
    cat = feat.ventas_mensuales(
        datos["facturas"], datos["lineas_factura"], nivel="categoria"
    )
    assert len({r["clave"] for r in prod}) > 5
    assert len({r["clave"] for r in cat}) >= 3
    assert all(r["total"] >= 0 for r in prod + cat)


def test_matriz_mensual_rellena_ceros(tmp_path):
    datos = _datos(tmp_path)
    matriz = feat.matriz_mensual(
        datos["facturas"], datos["lineas_factura"], nivel="total"
    )
    assert matriz["periodos"]
    assert len(matriz["valores"]["total"]) == len(matriz["periodos"])
    # La serie total no tiene huecos: todos los meses tienen valor >= 0.
    assert all(v >= 0 for v in matriz["valores"]["total"])


def test_nivel_invalido_falla():
    with pytest.raises(ValueError):
        feat.ventas_mensuales([], nivel="cliente")
