"""Intenciones por palabras clave (paso 0; se arma en el paso 4).

Módulo app.ml.asistente. Dueño: Fernando (Módulo 4). Depende de asistente/catalogo.py.
Línea base sin modelo: palabras clave y fechas.
"""
from __future__ import annotations

import calendar
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.ml.asistente.catalogo import CATALOGO

UMBRAL_CONFIANZA = 0.5
FECHA_INVALIDA = "_fecha_invalida"

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

_PATRON_FECHA_COMPLETA = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
_PATRON_RANGO = re.compile(
    r"\b(?:entre|de)\s+([a-z]+)\s+(?:y|a)\s+([a-z]+)\s+(?:de\s+)?(20\d{2})\b"
)
_PATRON_AnioMes = re.compile(r"\b(20\d{2})[-/](\d{1,2})\b")
_PATRON_ANIO = re.compile(r"\b(20\d{2})\b")
_PATRON_CLIENTE = re.compile(r"\bcliente\s*(?:n[°ºo]?\.?\s*)?(\d+)\b")
_PATRON_CLIENTE_TEXTO = re.compile(
    r"\bcliente\s+([a-z0-9]+(?:\.[a-z0-9]+)*\.?"
    r"(?:\s+[a-z0-9]+(?:\.[a-z0-9]+)*\.?){0,3})"
)
_PATRON_TOP = re.compile(r"\btop\s*(\d+)\b")
PALABRAS_CLIENTE_IGNORADAS = frozenset(
    {
        "de",
        "del",
        "por",
        "en",
        "un",
        "una",
        "con",
        "para",
        "durante",
        "este",
        "esta",
        "estos",
        "estas",
        "mes",
        "ano",
        "anio",
        "hoy",
        "ayer",
    }
)
ARTICULOS_CLIENTE = frozenset({"el", "la", "los", "las", "a", "y"})

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


def extraer_fechas(texto: str, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    parametros = {}

    completa = _PATRON_FECHA_COMPLETA.search(texto)
    if completa:
        anio, mes, dia = (int(grupo) for grupo in completa.groups())
        try:
            fecha = date(anio, mes, dia)
        except ValueError:
            return {FECHA_INVALIDA: True}
        return {"anio": fecha.year, "mes": fecha.month, "dia": fecha.day}

    rango = _PATRON_RANGO.search(texto)
    if rango:
        primero = MESES.get(rango.group(1))
        ultimo = MESES.get(rango.group(2))
        anio = int(rango.group(3))
        if not primero or not ultimo or primero > ultimo:
            return {FECHA_INVALIDA: True}
        parametros["desde"] = date(anio, primero, 1).isoformat()
        parametros["hasta"] = date(
            anio, ultimo, calendar.monthrange(anio, ultimo)[1]
        ).isoformat()
        return parametros

    anio_mes = _PATRON_AnioMes.search(texto)
    if anio_mes:
        anio, mes = int(anio_mes.group(1)), int(anio_mes.group(2))
        if not 1 <= mes <= 12:
            return {FECHA_INVALIDA: True}
        parametros.update({"anio": anio, "mes": mes})
        return parametros

    if "ayer" in texto:
        fecha = hoy - timedelta(days=1)
        parametros.update({"anio": fecha.year, "mes": fecha.month, "dia": fecha.day})
        return parametros
    if "hoy" in texto:
        parametros.update({"anio": hoy.year, "mes": hoy.month, "dia": hoy.day})
        return parametros
    if "este mes" in texto:
        parametros.update({"anio": hoy.year, "mes": hoy.month})
        return parametros
    if "ano pasado" in texto:
        parametros["anio"] = hoy.year - 1
        return parametros
    if "este ano" in texto:
        parametros["anio"] = hoy.year
        return parametros

    for nombre, numero in MESES.items():
        if re.search(rf"\b{nombre}\b", texto):
            parametros.update({"mes": numero, "anio": hoy.year})
            break

    anio = _PATRON_ANIO.search(texto)
    if anio:
        parametros["anio"] = int(anio.group(1))
    return parametros


def _extraer_cliente_texto(texto):
    encontrado = _PATRON_CLIENTE_TEXTO.search(texto)
    if encontrado is None:
        return None
    palabras = []
    for palabra in encontrado.group(1).split():
        if palabra.strip(".").casefold() in PALABRAS_CLIENTE_IGNORADAS:
            break
        palabras.append(palabra)
    while palabras and palabras[-1].strip(".").isdigit():
        palabras.pop()
    if not palabras:
        return None
    if all(palabra.strip(".").casefold() in ARTICULOS_CLIENTE for palabra in palabras):
        return None
    return " ".join(palabras).rstrip(".")


def extraer_parametros(texto: str, hoy: date | None = None) -> dict:
    parametros = extraer_fechas(texto, hoy)
    if FECHA_INVALIDA in parametros:
        return parametros

    cliente = _PATRON_CLIENTE.search(texto)
    if cliente:
        parametros["cliente_id"] = int(cliente.group(1))
    else:
        nombre = _extraer_cliente_texto(texto)
        if nombre:
            parametros["cliente"] = nombre

    top = _PATRON_TOP.search(texto)
    if top:
        parametros["n"] = int(top.group(1))
    return parametros


def clasificar(pregunta: str, hoy: date | None = None) -> Intencion | None:
    texto = normalizar(pregunta)
    if not texto:
        return None

    parametros = extraer_parametros(texto, hoy)
    if FECHA_INVALIDA in parametros:
        return None

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
