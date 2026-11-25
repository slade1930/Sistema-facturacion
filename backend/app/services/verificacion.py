"""Código de verificación de facturas: HMAC-SHA256 truncado a 12 caracteres.
La clave proviene de la variable de entorno FACTURA_HMAC_KEY — NUNCA hardcodeada
ni subida al repositorio. Si falta la variable, lanza error explícito.
"""
import hashlib
import hmac
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

LARGO_CODIGO = 12  # factura.codigo_verificacion es String(12)
_CENTAVO = Decimal("0.01")


def _clave() -> bytes:
    # Lee la clave secreta sin exponerla ni dejarla almacenada en el código.
    clave = os.getenv("FACTURA_HMAC_KEY", "").strip()
    if not clave:
        raise RuntimeError(
            "Falta FACTURA_HMAC_KEY en el entorno; no se puede firmar la factura"
        )
    return clave.encode("utf-8")


def _normalizar_total(total: Decimal | int | float | str) -> str:
    # Redondea el total a dos decimales para generar siempre el mismo mensaje.
    try:
        valor = Decimal(str(total))
        if not valor.is_finite():
            raise ValueError("El total debe ser un número finito.")
        return format(valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP), ".2f")
    except InvalidOperation as error:
        raise ValueError("El total no es válido para generar el código.") from error


def generar_codigo_verificacion(
    numero_serie: str,
    total: Decimal | int | float | str,
    cliente_ruc: str = "",
) -> str:
    """Firma determinista: mismo folio + total + RUC produce el mismo código."""
    # Combina los datos identificadores antes de calcular la firma HMAC.
    mensaje = (
        f"{numero_serie}|{_normalizar_total(total)}|{cliente_ruc or ''}"
    ).encode("utf-8")
    # Trunca el HMAC-SHA256 al tamaño admitido por la factura.
    digest = hmac.new(_clave(), mensaje, hashlib.sha256).hexdigest().upper()
    return digest[:LARGO_CODIGO]


def validar_codigo_verificacion(
    codigo: str,
    numero_serie: str,
    total: Decimal | int | float | str,
    cliente_ruc: str = "",
) -> bool:
    """Valida el código frente a la serie, total y RUC de la factura."""
    # Rechaza tipos o formatos que no correspondan al código de verificación.
    if not isinstance(codigo, str):
        return False

    recibido = codigo.strip().upper()
    if len(recibido) != LARGO_CODIGO or any(
        caracter not in "0123456789ABCDEF" for caracter in recibido
    ):
        return False

    esperado = generar_codigo_verificacion(numero_serie, total, cliente_ruc)
    # Compara en tiempo constante para evitar revelar diferencias de forma temprana.
    return hmac.compare_digest(esperado, recibido)
