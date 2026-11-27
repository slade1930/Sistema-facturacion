"""Compatibilidad: la fuente oficial de validadores es app.utils.validators.

Este módulo solo re-exporta para no romper imports existentes
(p. ej. app.services.totales). Código nuevo debe importar desde
`app.utils.validators` directamente.
"""

from app.utils.validators import *  # noqa: F401,F403
