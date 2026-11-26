import logging
import sys

_configurado = False


def configurar_logging():
    global _configurado
    if _configurado:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    _configurado = True


def get_logger(nombre):
    return logging.getLogger(nombre)