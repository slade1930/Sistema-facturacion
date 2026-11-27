from datetime import date

import pytest

from app.ml.asistente import catalogo, intenciones
from app.ml.asistente.frases_entrenamiento import FRASES_ROTULOADAS, FRASES_VALIDACION
from app.ml.entrenamiento import entrenar_asistente
from app.ml.modelos import asistente as modelo

HOY = date(2026, 11, 26)
NOMBRE_PRUEBA = "asistente_prueba.pt"


@pytest.fixture(scope="module")
def modelo_entrenado(tmp_path_factory):
    pytest.importorskip("torch")
    carpeta = tmp_path_factory.mktemp("asistente")
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(modelo, "CARPETA_MODELOS", carpeta)
        datos = entrenar_asistente.entrenar_asistente(guardar=False, epocas=400)
        if datos is None:
            pytest.skip("sin torch")
        ruta = modelo.guardar(datos, NOMBRE_PRUEBA)
        parche.setattr(modelo, "cargar_modelo", lambda nombre: ruta)
        yield ruta


def test_frases_rotuladas_cubren_las_seis_intenciones():
    etiquetas = {etiqueta for _, etiqueta in FRASES_ROTULOADAS}
    assert etiquetas == set(catalogo.INTENCIONES)
    assert len(FRASES_ROTULOADAS) == 54
    for nombre in catalogo.INTENCIONES:
        assert sum(1 for _, etiqueta in FRASES_ROTULOADAS if etiqueta == nombre) == 9
    assert all(isinstance(frase, str) and frase.strip() for frase, _ in FRASES_ROTULOADAS)


def test_validacion_esta_separada_del_entrenamiento():
    assert len(FRASES_VALIDACION) == 12
    assert {etiqueta for _, etiqueta in FRASES_VALIDACION} == set(catalogo.INTENCIONES)
    for nombre in catalogo.INTENCIONES:
        assert sum(1 for _, etiqueta in FRASES_VALIDACION if etiqueta == nombre) == 2
    entrenamiento = {frase.strip().casefold() for frase, _ in FRASES_ROTULOADAS}
    validacion = {frase.strip().casefold() for frase, _ in FRASES_VALIDACION}
    assert entrenamiento.isdisjoint(validacion)


def test_vocabulario_y_bolsa_de_palabras():
    vocabulario = modelo.vocabulario_desde(["Ventas por mes", "ventas del cliente"])
    assert set(vocabulario) == {"ventas", "por", "mes", "del", "cliente"}
    vector = modelo.vectorizar("VENTAS POR MES", vocabulario)
    assert len(vector) == len(vocabulario)
    assert sum(vector) == 3.0


def test_tokenizar_quita_signos_y_acentos():
    assert modelo.tokenizar("¿Cuánto facturamos en octubre de 2026?") == [
        "cuanto",
        "facturamos",
        "en",
        "octubre",
        "de",
        "2026",
    ]
    assert modelo.tokenizar("Ventas del 2026-10-05, ¿no?") == [
        "ventas",
        "del",
        "2026",
        "10",
        "05",
        "no",
    ]


def test_sin_modelo_no_predice(monkeypatch):
    monkeypatch.setattr(modelo, "cargar_modelo", lambda nombre: None)
    assert modelo.predecir("ventas por mes") is None


def test_sin_torch_no_predice_ni_guarda(monkeypatch):
    monkeypatch.setattr(modelo, "torch", None)
    assert modelo.disponible() is False
    assert modelo.ajustar([], []) is None
    assert modelo.guardar({"datos": 1}) is None
    assert modelo.predecir("ventas por mes") is None
    assert entrenar_asistente.entrenar_asistente(guardar=False) is None


def test_entrenamiento_es_reproducible():
    torch = pytest.importorskip("torch")
    frases = [frase for frase, _ in FRASES_ROTULOADAS]
    etiquetas = [etiqueta for _, etiqueta in FRASES_ROTULOADAS]
    primero = modelo.ajustar(
        frases, etiquetas, epocas=50, semilla=modelo.SEMILLA
    )
    segundo = modelo.ajustar(
        frases, etiquetas, epocas=50, semilla=modelo.SEMILLA
    )
    otro = modelo.ajustar(
        frases, etiquetas, epocas=50, semilla=modelo.SEMILLA + 1
    )
    assert primero["vocabulario"] == segundo["vocabulario"]
    assert primero["clases"] == segundo["clases"]
    for clave, valor in primero["estado"].items():
        assert torch.equal(valor, segundo["estado"][clave])
    assert any(
        not torch.equal(valor, otro["estado"][clave])
        for clave, valor in primero["estado"].items()
    )


def test_ajustar_valida_entradas():
    pytest.importorskip("torch")
    assert modelo.ajustar([], []) is None
    assert modelo.ajustar(["ventas por mes"], []) is None
    assert modelo.ajustar(["ventas por mes"], ["no_existe"]) is None
    assert modelo.ajustar(["   "], ["ventas_por_mes"]) is None


def test_guardar_usa_solo_el_nombre_del_archivo(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    monkeypatch.setattr(modelo, "CARPETA_MODELOS", tmp_path)
    datos = {"vocabulario": {}, "clases": [], "estado": {}}
    ruta = modelo.guardar(datos, "../fuera.pt")
    assert ruta == tmp_path / "fuera.pt"
    assert ruta.is_file()


def test_red_local_aprende_y_predice(modelo_entrenado):
    for frase, esperado in FRASES_ROTULOADAS:
        resultado = modelo.predecir(frase, NOMBRE_PRUEBA, hoy=HOY)
        assert resultado is not None
        assert resultado.nombre == esperado
        assert resultado.confianza >= modelo.UMBRAL_CONFIANZA


def test_red_local_generaliza_en_validacion(modelo_entrenado):
    aciertos = 0
    for frase, esperado in FRASES_VALIDACION:
        resultado = modelo.predecir(frase, NOMBRE_PRUEBA, hoy=HOY)
        if resultado is not None and resultado.nombre == esperado:
            aciertos += 1
    assert aciertos == len(FRASES_VALIDACION)


def test_modelo_no_peor_que_la_linea_base(modelo_entrenado):
    aciertos_modelo = 0
    aciertos_base = 0
    for frase, esperado in FRASES_VALIDACION:
        prediccion = modelo.predecir(frase, NOMBRE_PRUEBA, hoy=HOY)
        base = intenciones.clasificar(frase, hoy=HOY)
        aciertos_modelo += prediccion is not None and prediccion.nombre == esperado
        aciertos_base += base is not None and base.nombre == esperado
    assert aciertos_modelo >= aciertos_base


@pytest.mark.parametrize(
    "frase, nombre, parametros",
    [
        (
            "ventas por mes en octubre de 2026",
            "ventas_por_mes",
            {"mes": 10, "anio": 2026},
        ),
        ("ventas de este año", "ventas_por_mes", {"anio": 2026}),
        ("ventas por cliente Acme", "ventas_por_cliente", {"cliente": "acme"}),
        ("Ventas del cliente 3", "ventas_por_cliente", {"cliente_id": 3}),
        ("ventas por cliente Acme S.A.", "ventas_por_cliente", {"cliente": "acme s.a"}),
        (
            "ventas por cliente Acme Sur en 2026",
            "ventas_por_cliente",
            {"cliente": "acme sur", "anio": 2026},
        ),
        ("facturas anuladas en 2026", "facturas_anuladas", {"anio": 2026}),
        ("top 3 productos en 2026", "top_productos", {"anio": 2026, "n": 3}),
        ("facturas en revisión", "facturas_en_revision", {}),
    ],
)
def test_parametros_vienen_de_la_intencion_predicha(
    modelo_entrenado, frase, nombre, parametros
):
    resultado = modelo.predecir(frase, NOMBRE_PRUEBA, hoy=HOY)
    assert resultado is not None
    assert resultado.nombre == nombre
    assert resultado.parametros == parametros


@pytest.mark.parametrize(
    "frase", ["ventas del 2026-02-31", "ventas de 2026-13"]
)
def test_fechas_invalidas_no_predicen(modelo_entrenado, frase):
    assert modelo.predecir(frase, NOMBRE_PRUEBA, hoy=HOY) is None


def test_frase_vacia_o_desconocida_no_predice(modelo_entrenado):
    for frase in ("", "   ", "xyzqv zzzzz"):
        assert modelo.predecir(frase, NOMBRE_PRUEBA, hoy=HOY) is None


def test_archivo_corrupto_no_rompe(tmp_path, monkeypatch):
    ruta = tmp_path / "roto.pt"
    ruta.write_bytes(b"no es un pickle")
    monkeypatch.setattr(modelo, "cargar_modelo", lambda nombre: ruta)
    assert modelo.predecir("ventas por mes", "roto.pt", hoy=HOY) is None
