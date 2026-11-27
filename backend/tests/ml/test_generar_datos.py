"""Pruebas del generador de datos de ejemplo del módulo ML.

Sin base de datos: todo corre en memoria y con CSV temporales.
"""
import csv
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.ml.datasets import generar_datos as gd

SALIDA_REAL = gd.SALIDA  # backend/app/ml/datasets/generados (ignorada)


def _dataset_chico(n=120, semilla=gd.SEMILLA):
    return gd.construir_dataset(
        n_facturas=n, n_pedidos=10, semilla=semilla
    )


# ---------- Reproducibilidad ----------

def test_reproducibilidad_misma_semilla():
    a = _dataset_chico()
    b = _dataset_chico()
    assert json.dumps(a["facturas"], sort_keys=True, default=str) == json.dumps(
        b["facturas"], sort_keys=True, default=str
    )
    assert a["etiquetas_anomalias"] == b["etiquetas_anomalias"]


def test_semilla_distinta_cambia_datos():
    a = _dataset_chico(semilla=1)
    b = _dataset_chico(semilla=2)
    assert a["facturas"] != b["facturas"]


# ---------- Volumen, rango y estructura ----------

def test_volumen_y_rango_de_fechas():
    dataset = gd.construir_dataset(
        n_facturas=1000, n_pedidos=10, semilla=gd.SEMILLA
    )
    facturas = dataset["facturas"]
    assert len(facturas) == 1000

    fechas = [date.fromisoformat(f["fecha"]) for f in facturas]
    assert max(fechas) <= gd.HOY
    assert min(fechas) >= gd.HOY - timedelta(days=36 * 30)
    # El rango cubre al menos ~24 meses.
    assert (max(fechas) - min(fechas)).days >= 24 * 30


def test_catalogo_en_rangos_acordados():
    dataset = _dataset_chico()
    catalogo = dataset["catalogo"]
    assert 30 <= len(catalogo["productos"]) <= 60
    assert 20 <= len(catalogo["clientes"]) <= 40
    assert len(dataset["lineas_factura"]) > len(dataset["facturas"])


def test_lineas_cobrar_por_y_gravadas():
    dataset = _dataset_chico()
    cobrar_por = {l["cobrar_por"] for l in dataset["lineas_factura"]}
    assert cobrar_por <= {"unidad", "caja"}
    assert any(l["gravada"] for l in dataset["lineas_factura"])
    assert any(not l["gravada"] for l in dataset["lineas_factura"])


def test_estados_solo_emitida_y_anulada_con_marca():
    dataset = _dataset_chico()
    estados = {f["estado"] for f in dataset["facturas"]}
    assert estados <= {"emitida", "anulada"}
    assert "en_revision" not in estados
    for f in dataset["facturas"]:
        assert gd.MARCA_EJEMPLO in f["notas"]
        assert f["es_ejemplo"] is True
    anuladas = [f for f in dataset["facturas"] if f["estado"] == "anulada"]
    assert anuladas, "debe haber facturas anuladas inyectadas"
    assert all(f["fecha_anulacion"] for f in anuladas)


def test_estacionalidad_y_tendencia_presentes():
    dataset = gd.construir_dataset(
        n_facturas=1000, n_pedidos=10, semilla=gd.SEMILLA
    )
    por_mes = {}
    for f in dataset["facturas"]:
        mes = date.fromisoformat(f["fecha"]).month
        por_mes.setdefault(mes, []).append(float(f["total"]))
    promedios = {m: sum(v) / len(v) for m, v in por_mes.items()}
    assert max(promedios.values()) > 1.15 * min(promedios.values())


# ---------- CSV y etiquetas ----------

def test_escritura_csv_en_carpeta_generados(tmp_path):
    dataset = _dataset_chico()
    archivos = gd.escribir_csvs(dataset, tmp_path)
    nombres = {p.name for p in archivos}
    assert {
        "facturas_ejemplo.csv",
        "lineas_factura_ejemplo.csv",
        "pedidos_ejemplo.csv",
        "lineas_pedido_ejemplo.csv",
        "etiquetas_anomalias.csv",
    } <= nombres
    # Gente, en Docker vive en /app y no hay .gitignore: lo busco hacia arriba.
    padre_gitignore = None
    for padre in Path(__file__).resolve().parents:
        candidato = padre / ".gitignore"
        if candidato.is_file():
            padre_gitignore = candidato
            break
    if padre_gitignore is None:
        pytest.skip("No hay .gitignore sobre esta ruta (en Docker /app no lo trae).")
    gitignore = padre_gitignore.read_text()
    assert "backend/app/ml/datasets/generados/" in gitignore


def test_archivos_reales_en_generados():
    dataset = gd.construir_dataset(
        n_facturas=gd.CANTIDAD_FACTURAS, n_pedidos=50, semilla=gd.SEMILLA
    )
    gd.escribir_csvs(dataset, SALIDA_REAL)
    for nombre in (
        "facturas_ejemplo.csv",
        "lineas_factura_ejemplo.csv",
        "etiquetas_anomalias.csv",
    ):
        assert (SALIDA_REAL / nombre).is_file(), nombre


def test_etiquetas_anomalias_con_casos_raros():
    dataset = _dataset_chico()
    etiquetas = dataset["etiquetas_anomalias"]
    assert len(etiquetas) > 0
    tipos = {e["tipo_anomalia"] for e in etiquetas}
    assert tipos & {
        "total_muy_alto", "descuento_alto", "sin_itbms",
        "cliente_sin_ruc", "factura_anulada", "serie_duplicada",
    }
    # Las series duplicadas inyectadas están documentadas.
    assert "serie_duplicada" in tipos


def test_descuento_alto_si_aplica_descuento_real():
    """El caso raro tiene que verse en las líneas y en el total."""
    dataset = gd.construir_dataset(n_facturas=250, n_pedidos=10)
    por_id = {f["id"]: f for f in dataset["facturas"]}
    ids = [
        int(e["factura_id"]) for e in dataset["etiquetas_anomalias"]
        if e["tipo_anomalia"] == "descuento_alto"
    ]

    assert ids, "la muestra debe incluir el caso descuento_alto"
    for fid in ids:
        factura = por_id[fid]
        assert factura["lineas"]
        assert all(
            Decimal(linea["descuento_pct"]) >= Decimal("40")
            for linea in factura["lineas"]
        )
        subtotal = Decimal(factura["subtotal"])
        descuento = Decimal(factura["descuento_total"])
        assert subtotal > 0
        assert descuento / subtotal >= Decimal("0.4")


def test_numeros_de_verificacion_reales_de_12_chars():
    dataset = _dataset_chico(60)
    for f in dataset["facturas"][:20]:
        assert len(f["codigo_verificacion"]) == 12
        assert all(c in "0123456789ABCDEF" for c in f["codigo_verificacion"])


# ---------- Validación ----------

def test_validacion_pasa_en_dataset_generado():
    dataset = _dataset_chico()
    errores = gd.validar_dataset(
        dataset["facturas"], dataset["etiquetas_anomalias"]
    )
    assert errores == []


def test_validacion_detecta_total_descuadrado():
    dataset = _dataset_chico(60)
    dataset["facturas"][0]["total"] = "9999.99"
    errores = gd.validar_dataset(
        dataset["facturas"], dataset["etiquetas_anomalias"]
    )
    assert any("total" in e for e in errores)


def test_validacion_detecta_monto_linea_descuadrado():
    dataset = _dataset_chico(60)
    dataset["facturas"][0]["lineas"][0]["monto"] = "0.01"
    errores = gd.validar_dataset(
        dataset["facturas"], dataset["etiquetas_anomalias"]
    )
    assert any("monto" in e for e in errores)


def test_validacion_detecta_serie_duplicada_sin_etiqueta():
    dataset = _dataset_chico(150)
    sin_etiquetas = [e for e in dataset["etiquetas_anomalias"]
                     if e["tipo_anomalia"] != "serie_duplicada"]
    errores = gd.validar_dataset(dataset["facturas"], sin_etiquetas)
    assert any("duplicado" in e for e in errores)


def test_validacion_detecta_fecha_fuera_de_rango():
    dataset = _dataset_chico(60)
    dataset["facturas"][0]["fecha"] = "2010-01-01"
    errores = gd.validar_dataset(
        dataset["facturas"], dataset["etiquetas_anomalias"]
    )
    assert any("fuera de rango" in e for e in errores)


def test_validacion_archivos_csv(tmp_path):
    dataset = _dataset_chico()
    gd.escribir_csvs(dataset, tmp_path)
    assert gd.validar_archivos(tmp_path) == []


# ---------- Anexado de registros nuevos ----------

def test_anexar_facturas_nuevas(tmp_path):
    dataset = _dataset_chico(60)
    gd.escribir_csvs(dataset, tmp_path)

    # Nueva factura "de prueba": misma estructura, totales recalculados
    # con los servicios reales y serie nueva (sin sesión Postgres).
    # Los contadores arrancan donde quedó el dataset para no duplicar.
    contadores = {}
    for f in dataset["facturas"]:
        anio, num = f["numero_serie"].split("-")[1:]
        anio, num = int(anio), int(num)
        contadores[anio] = max(contadores.get(anio, 0), num)

    import random as _random
    rng = _random.Random(7)
    facturas_nuevas, _ = gd.construir_facturas(
        dataset["catalogo"]["productos"], dataset["catalogo"]["clientes"],
        3, rng, contadores=contadores, inicio_id=999,
    )
    errores = gd.anexar_facturas_csv(facturas_nuevas, tmp_path)
    assert errores == []

    facturas, etiquetas = gd.leer_dataset_csv(tmp_path)
    assert len(facturas) == 63
    series = [f["numero_serie"] for f in facturas]
    assert len(set(series)) == len(series)


def test_anexar_detecta_inconsistencia_en_nueva(tmp_path):
    dataset = _dataset_chico(60)
    gd.escribir_csvs(dataset, tmp_path)

    mala = {
        "id": "9999",
        "numero_serie": "FAC-2026-9999",
        "codigo_verificacion": "A" * 12,
        "fecha": "2026-06-01",
        "cliente_nombre": "Cliente malo",
        "cliente_ruc": None,
        "mostrar_ruc": True,
        "cliente_direccion": None,
        "cliente_telefono": None,
        "cliente_correo": None,
        "sucursal": None,
        "vendedor": None,
        "orden_compra": None,
        "condicion_pago": "contado",
        "portes": "0.00",
        "notas": "[DATOS DE EJEMPLO] - manual",
        "subtotal": "100.00",
        "descuento_total": "0.00",
        "base_gravada": "100.00",
        "base_exenta": "0.00",
        "itbms": "7.00",
        "total": "107.00",
        "estado": "emitida",
        "fecha_creacion": "2026-06-01T08:00:00",
        "fecha_anulacion": None,
        "es_ejemplo": True,
        "caso_raro": None,
        "lineas": [{
            "id": "1", "factura_id": "9999", "orden": "1",
            "descripcion": "X", "codigo_barras": None, "categoria": None,
            "cantidad": "1", "precio_unitario": "100.00",
            "precio_unidad": "100.00", "descuento_pct": "0.00",
            "gravada": True, "unidades_por_caja": "1",
            "cobrar_por": "unidad", "monto": "50.00",
            "producto_id": None, "es_ejemplo": True,
        }],
    }
    errores = gd.anexar_facturas_csv([mala], tmp_path)
    assert errores, "debió detectar el monto descuadrado de la línea nueva"
