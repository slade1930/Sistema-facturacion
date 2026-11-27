"""Intenciones por palabras clave (paso 0; se arma en el paso 4).

Módulo app.ml.asistente. Dueño: Fernando (Módulo 4). Depende de asistente/catalogo.py.
Línea base sin modelo: palabras clave y fechas.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.ml.asistente.catalogo import CATALOGO

UMBRAL_CONFIANZA = 0.5

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_PATRON_AnioMes = re.compile(r"\b(20\d{2})[-/](\d{1,2})\b")
_PATRON_ANIO = re.compile(r"\b(20\d{2})\b")
_PATRON_CLIENTE = re.compile(r"\bcliente\s*(?:n[°ºo]?\.?\s*)?(\d+)\b")
_PATRON_TOP = re.compile(r"\btop\s*(\d+)\b")

REGLAS = (
    (("en revision", "en_revision"), "facturas_en_revision", 0.95),
    (("anulad",), "facturas_anuladas", 0.90),
    (("mas vendid", "top "), "top_productos", 0.90),
    (("por producto",), "ventas_por_producto", 0.90),
    (("por cliente", "del cliente", "cliente "), "ventas_por_cliente", 0.85),
    (("por mes", "facturamos", "cuanto factur", "ventas"), "ventas_por_mes", 0.80),
)


@dataclass(frozen=True)
class Intencion:
    nombre: str
    confianza: float
    parametros: dict = field(default_factory=dict)


def normalizar(texto: str) -> str:
    sin_acentos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(caracter) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_acentos).strip()


def extraer_fechas(texto: str) -> dict:
    parametros = {}
    anio_mes = _PATRON_AnioMes.search(texto)
    if anio_mes:
        anio, mes = int(anio_mes.group(1)), int(anio_mes.group(2))
        if 1 <= mes <= 12:
            parametros["anio"] = anio
            parametros["mes"] = mes
        return parametros

    for nombre, numero in MESES.items():
        if re.search(rf"\b{nombre}\b", texto):
            parametros["mes"] = numero
            break

    anio = _PATRON_ANIO.search(texto)
    if anio:
        parametros["anio"] = int(anio.group(1))
    return parametros


def clasificar(pregunta: str) -> Intencion | None:
    texto = normalizar(pregunta)
    if not texto:
        return None

    parametros = extraer_fechas(texto)

    cliente = _PATRON_CLIENTE.search(texto)
    if cliente:
        parametros["cliente"] = cliente.group(1)

    top = _PATRON_TOP.search(texto)
    if top:
        parametros["n"] = int(top.group(1))

    for claves, nombre, confianza in REGLAS:
        if any(clave in texto for clave in claves):
            return Intencion(nombre, confianza, parametros)
    return None


def ejecutar(db, clasificacion: Intencion | None):
    if clasificacion is None:
        return None
    if clasificacion.confianza < UMBRAL_CONFIANZA:
        return None
    consulta = CATALOGO.get(clasificacion.nombre)
    if consulta is None:
        return None
    return consulta(db, **clasificacion.parametros)
