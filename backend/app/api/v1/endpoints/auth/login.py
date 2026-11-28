"""Inicio de sesión con nombre de empresa y contraseña. Público; etapa A."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.v1.deps import ip_para_limite
from app.core.constants import API_KEY_HEADER
from app.db.session import get_db
from app.schemas.auth import LoginEntrada, SesionSalida
from app.schemas.empresa import resumen_empresa
from app.services.auth import (
    crear_sesion,
    limpiar_intentos,
    limpiar_sesiones_vencidas,
    normalizar_nombre_usuario,
    registrar_auditoria,
    registrar_fallo,
    segundos_bloqueo,
    verificar_credenciales,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

MENSAJE_GENERICO = "Empresa o contraseña incorrectos"


@router.post("/login", response_model=SesionSalida)
def iniciar_sesion(
    datos: LoginEntrada,
    request: Request,
    db: Session = Depends(get_db),
):
    limpiar_sesiones_vencidas(db)
    ip = ip_para_limite(request, request.headers.get(API_KEY_HEADER))
    nombre = normalizar_nombre_usuario(datos.nombre_empresa)
    restante = segundos_bloqueo(ip, nombre)
    if restante:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos. Intenta de nuevo en {restante} segundos.",
            headers={"Retry-After": str(restante)},
        )

    cuenta = verificar_credenciales(db, datos.nombre_empresa, datos.contrasena)
    if cuenta is None:
        registrar_fallo(ip, nombre)
        registrar_auditoria(
            db, "login_fallo", detalle=f"Intento con {nombre}", ip=ip
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAJE_GENERICO
        )

    limpiar_intentos(ip, nombre)
    token, sesion = crear_sesion(db, cuenta)
    cuenta.ultimo_acceso = sesion.creada_en
    registrar_auditoria(
        db,
        "login_ok",
        cuenta_id=cuenta.id,
        detalle=f"Inicio de sesión de {nombre}",
        ip=ip,
    )
    db.commit()
    return SesionSalida(
        token=token,
        rol=cuenta.rol.value,
        cuenta_id=cuenta.id,
        empresa=resumen_empresa(cuenta.cliente) if cuenta.cliente else None,
        debe_cambiar_clave=cuenta.debe_cambiar_clave,
    )
