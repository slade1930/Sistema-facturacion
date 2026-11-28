"""Contraseñas, tokens, sesiones y límite de intentos. Portal; etapa A."""

import base64
import hashlib
import hmac
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.seguridad import Cuenta, Sesion
from app.repositories.cuentas import (
    AuditoriaRepository,
    CuentasRepository,
    SesionesRepository,
)

INACTIVIDAD = timedelta(minutes=30)
DURACION_ABSOLUTA = timedelta(hours=12)
ACTUALIZACION_MINIMA = timedelta(minutes=1)
MAX_FALLOS = 5
VENTANA_FALLOS = timedelta(minutes=15)
TIEMPO_BLOQUEO = timedelta(minutes=30)

# Límite en memoria: por proceso, no compartido entre réplicas del backend.
_intentos: dict[tuple[str, str], list[datetime]] = defaultdict(list)
_bloqueos: dict[tuple[str, str], datetime] = {}


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _utc(valor: datetime) -> datetime:
    return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)


def _iteraciones() -> int:
    return int(getattr(settings, "AUTH_PBKDF2_ITERATIONS", 600_000))


# ---------- Contraseña ----------

def normalizar_nombre_usuario(valor: str) -> str:
    """Nombre de empresa o usuario sin espacios sobrantes y en minúsculas."""
    return " ".join((valor or "").strip().split()).lower()


def faltantes_politica_clave(clave: str) -> list[str]:
    """Devuelve qué reglas faltan; vacío si la contraseña es válida."""
    faltan = []
    if clave is None or not 8 <= len(clave) <= 64:
        faltan.append("tener entre 8 y 64 caracteres")
    if not any(caracter.isupper() for caracter in clave or ""):
        faltan.append("incluir al menos una mayúscula")
    if not any(caracter.isdigit() for caracter in clave or ""):
        faltan.append("incluir al menos un número")
    return faltan


def validar_politica_clave(clave: str) -> None:
    faltan = faltantes_politica_clave(clave)
    if faltan:
        raise ValueError("La contraseña debe " + "; ".join(faltan) + ".")


def hash_clave(clave: str) -> str:
    iteraciones = _iteraciones()
    sal = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", (clave or "").encode("utf-8"), sal, iteraciones
    )
    return "pbkdf2_sha256${}${}${}".format(
        iteraciones,
        base64.b64encode(sal).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


@lru_cache(maxsize=8)
def _hash_falso(iteraciones: int) -> str:
    """Hash de una clave inexistente para igualar el tiempo de respuesta."""
    sal = b"salt-falso-portal-empresas"
    digest = hashlib.pbkdf2_hmac("sha256", b"clave-inexistente", sal, iteraciones)
    return "pbkdf2_sha256${}${}${}".format(
        iteraciones,
        base64.b64encode(sal).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verificar_clave(clave: str, guardado: str) -> bool:
    try:
        algoritmo, iteraciones_txt, sal_txt, hash_txt = (guardado or "").split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        iteraciones = int(iteraciones_txt)
        sal = base64.b64decode(sal_txt, validate=True)
        esperado = base64.b64decode(hash_txt, validate=True)
    except (ValueError, TypeError):
        return False
    calculado = hashlib.pbkdf2_hmac(
        "sha256", (clave or "").encode("utf-8"), sal, iteraciones
    )
    return hmac.compare_digest(calculado, esperado)


def verificar_credenciales(db: Session, nombre: str, clave: str) -> Cuenta | None:
    cuenta = CuentasRepository(db).por_nombre_usuario(
        normalizar_nombre_usuario(nombre)
    )
    guardado = cuenta.password_hash if cuenta else _hash_falso(_iteraciones())
    coincide = verificar_clave(clave, guardado)
    if cuenta is None or not cuenta.activo or not coincide:
        return None
    return cuenta


# ---------- Tokens y sesiones ----------

def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def crear_sesion(
    db: Session, cuenta: Cuenta, ahora: datetime | None = None
) -> tuple[str, Sesion]:
    ahora = _utc(ahora or ahora_utc())
    token = secrets.token_urlsafe(32)
    sesion = Sesion(
        cuenta_id=cuenta.id,
        token_hash=hash_token(token),
        creada_en=ahora,
        ultima_actividad=ahora,
        expira_en=ahora + DURACION_ABSOLUTA,
        revocada=False,
    )
    SesionesRepository(db).crear(sesion)
    return token, sesion


def obtener_sesion_valida(
    db: Session, token: str | None, ahora: datetime | None = None
) -> tuple[Cuenta, Sesion] | None:
    if not token:
        return None
    ahora = _utc(ahora or ahora_utc())
    repositorio = SesionesRepository(db)
    sesion = repositorio.por_token_hash(hash_token(token))
    if sesion is None or sesion.revocada:
        return None
    cuenta = CuentasRepository(db).por_id(sesion.cuenta_id)
    if cuenta is None or not cuenta.activo:
        return None
    actividad = _utc(sesion.ultima_actividad)
    if ahora >= _utc(sesion.expira_en) or ahora - actividad > INACTIVIDAD:
        return None
    if ahora - actividad >= ACTUALIZACION_MINIMA:
        repositorio.marcar_actividad(sesion.id, ahora)
        # La actividad se guarda antes de entrar al endpoint; todavía no hay
        # cambios parciales de la petición en esta sesión.
        db.commit()
    return cuenta, sesion


def cerrar_sesion(db: Session, token: str) -> None:
    SesionesRepository(db).revocar_token(hash_token(token))


def revocar_sesiones(
    db: Session, cuenta_id: int, token_actual: str | None = None
) -> None:
    excluido = hash_token(token_actual) if token_actual else None
    SesionesRepository(db).revocar(cuenta_id, excepto_hash=excluido)


def cambiar_clave(
    db: Session, cuenta: Cuenta, nueva_clave: str, token_actual: str | None = None
) -> None:
    validar_politica_clave(nueva_clave)
    cuenta.password_hash = hash_clave(nueva_clave)
    cuenta.debe_cambiar_clave = False
    revocar_sesiones(db, cuenta.id, token_actual)


def desactivar_cuenta(db: Session, cuenta: Cuenta) -> None:
    cuenta.activo = False
    revocar_sesiones(db, cuenta.id)


def activar_cuenta(db: Session, cuenta: Cuenta) -> None:
    cuenta.activo = True


# ---------- Auditoría ----------

def registrar_auditoria(
    db: Session,
    accion: str,
    *,
    cuenta_id: int | None = None,
    detalle: str | None = None,
    ip: str | None = None,
) -> None:
    AuditoriaRepository(db).registrar(
        accion, cuenta_id=cuenta_id, detalle=detalle, ip=ip
    )


# ---------- Límite de intentos ----------

def _clave_limite(tipo: str, valor: str | None) -> tuple[str, str]:
    return (tipo, (valor or "desconocido").strip().lower()[:100])


def _limpiar(ahora: datetime) -> None:
    for clave, momentos in list(_intentos.items()):
        recientes = [momento for momento in momentos if ahora - momento < VENTANA_FALLOS]
        if recientes:
            _intentos[clave] = recientes
        else:
            _intentos.pop(clave, None)
    for clave, hasta in list(_bloqueos.items()):
        if hasta <= ahora:
            _bloqueos.pop(clave, None)


def segundos_bloqueo(
    ip: str | None, nombre: str | None, ahora: datetime | None = None
) -> int:
    ahora = _utc(ahora or ahora_utc())
    _limpiar(ahora)
    claves = (_clave_limite("ip", ip), _clave_limite("nombre", nombre))
    vigentes = [_bloqueos[clave] for clave in claves if clave in _bloqueos]
    if not vigentes:
        return 0
    return max(1, int((max(vigentes) - ahora).total_seconds()) + 1)


def registrar_fallo(
    ip: str | None, nombre: str | None, ahora: datetime | None = None
) -> None:
    ahora = _utc(ahora or ahora_utc())
    claves = (_clave_limite("ip", ip), _clave_limite("nombre", nombre))
    for clave in claves:
        _intentos[clave].append(ahora)
    if any(len(_intentos[clave]) >= MAX_FALLOS for clave in claves):
        for clave in claves:
            _bloqueos[clave] = ahora + TIEMPO_BLOQUEO
            _intentos[clave] = []


def limpiar_intentos(ip: str | None, nombre: str | None) -> None:
    for clave in (_clave_limite("ip", ip), _clave_limite("nombre", nombre)):
        _intentos.pop(clave, None)
        _bloqueos.pop(clave, None)


def ip_de_la_peticion(request, confiar_en_forwarded: bool) -> str:
    """La IP detrás del proxy solo se acepta si la petición trajo API-Key válida."""
    if confiar_en_forwarded:
        cabecera = request.headers.get("X-Forwarded-For")
        if cabecera:
            return cabecera.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "desconocida")[:64]
