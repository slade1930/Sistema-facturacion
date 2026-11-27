import pytest

from app.ml.asistente import catalogo
from app.ml.asistente.frases_entrenamiento import FRASES_ROTULOADAS
from app.ml.entrenamiento import entrenar_asistente
from app.ml.modelos import asistente as modelo


def test_frases_rotuladas_cubren_las_seis_intenciones():
    etiquetas = {etiqueta for _, etiqueta in FRASES_ROTULOADAS}
    assert etiquetas == set(catalogo.INTENCIONES)
    assert all(isinstance(frase, str) and frase for frase, _ in FRASES_ROTULOADAS)


def test_vocabulario_y_bolsa_de_palabras():
    vocabulario = modelo.vocabulario_desde(["Ventas por mes", "ventas del cliente"])
    assert set(vocabulario) == {"ventas", "por", "mes", "del", "cliente"}
    vector = modelo.vectorizar("VENTAS POR MES", vocabulario)
    assert len(vector) == len(vocabulario)
    assert sum(vector) == 3.0


def test_sin_modelo_no_predice(monkeypatch):
    monkeypatch.setattr(modelo, "cargar_modelo", lambda nombre: None)
    assert modelo.predecir("ventas por mes") is None


def test_entrenamiento_sin_torch_no_guarda_nada(monkeypatch):
    monkeypatch.setattr(modelo, "torch", None)
    assert entrenar_asistente.entrenar_asistente(guardar=False) is None


def test_red_local_aprende_y_predice(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    monkeypatch.setattr(modelo, "CARPETA_MODELOS", tmp_path)
    frases = [frase for frase, _ in FRASES_ROTULOADAS]
    etiquetas = [etiqueta for _, etiqueta in FRASES_ROTULOADAS]
    datos = modelo.ajustar(frases, etiquetas, epocas=250)
    assert datos is not None
    ruta = modelo.guardar(datos, "asistente_prueba.pt")
    assert ruta.is_file()
    monkeypatch.setattr(modelo, "cargar_modelo", lambda nombre: ruta)
    resultado = modelo.predecir("facturas en revision", "asistente_prueba.pt")
    assert resultado is not None
    assert resultado.nombre == "facturas_en_revision"
    assert resultado.confianza >= modelo.UMBRAL_CONFIANZA
