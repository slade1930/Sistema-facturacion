"""Indicador de la política de contraseña del portal; etapa B."""

from typing import Any

from nicegui import ui


def cumple_politica(clave: str) -> bool:
    valor = str(clave or "")
    return (
        8 <= len(valor) <= 64
        and any(caracter.isupper() for caracter in valor)
        and any(caracter.isdigit() for caracter in valor)
    )


def indicador_clave(campo: Any) -> Any:
    """Explica la regla y marca en verde cuando la clave ya cumple."""
    etiqueta = ui.label(
        "Entre 8 y 64 caracteres, con al menos una mayúscula y un número."
    ).classes("orq-bloque-ayuda")

    def actualizar(evento: Any) -> None:
        if cumple_politica(evento.value):
            etiqueta.text = "La contraseña cumple los requisitos."
            etiqueta.classes(replace="orq-bloque-ayuda text-positive")
        else:
            etiqueta.text = (
                "Entre 8 y 64 caracteres, con al menos una mayúscula y un número."
            )
            etiqueta.classes(replace="orq-bloque-ayuda")

    campo.on_value_change(actualizar)
    return etiqueta


__all__ = ["cumple_politica", "indicador_clave"]
