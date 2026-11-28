"""Alta de empresa y su cuenta en una transacción. Público; etapa A."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import ip_para_limite
from app.core.constants import API_KEY_HEADER
from app.db.session import get_db
from app.models.catalogo import ClienteB2B
from app.models.seguridad import Cuenta, RolCuenta
from app.repositories.cuentas import CuentasRepository
from app.schemas.auth import SesionSalida
from app.schemas.empresa import EmpresaRegistro, resumen_empresa
from app.services.auth import (
    crear_sesion,
    hash_clave,
    normalizar_nombre_usuario,
    registrar_auditoria,
    registrar_fallo,
    segundos_bloqueo,
    validar_politica_clave,
)
from app.utils.validators import validar_correo, validar_ruc, validar_telefono

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=SesionSalida)
def registrar_empresa(
    datos: EmpresaRegistro,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = ip_para_limite(request, request.headers.get(API_KEY_HEADER))
    nombre = normalizar_nombre_usuario(datos.nombre_empresa)
    restante = segundos_bloqueo(ip, nombre)
    if restante:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos. Intenta de nuevo en {restante} segundos.",
            headers={"Retry-After": str(restante)},
        )

    validar_politica_clave(datos.contrasena)
    ruc = validar_ruc(datos.ruc)
    correo = validar_correo(datos.correo)
    telefono = validar_telefono(datos.telefono)

    if CuentasRepository(db).por_nombre_usuario(nombre) is not None or db.scalar(
        select(ClienteB2B).where(
            func.lower(func.trim(ClienteB2B.nombre_empresa)) == nombre
        )
    ) is not None:
        registrar_fallo(ip, nombre)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una empresa con ese nombre.",
        )
    if db.scalar(select(ClienteB2B).where(ClienteB2B.ruc == ruc)) is not None:
        registrar_fallo(ip, nombre)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una empresa con ese RUC.",
        )

    cliente = ClienteB2B(
        nombre_empresa=datos.nombre_empresa.strip(),
        ruc=ruc,
        email_contacto=correo,
        telefono=telefono,
        direccion=datos.direccion,
        sucursal=datos.sucursal,
        sector=datos.sector,
        activo=True,
    )
    db.add(cliente)
    db.flush()

    cuenta = Cuenta(
        nombre_usuario=nombre,
        password_hash=hash_clave(datos.contrasena),
        rol=RolCuenta.EMPRESA,
        cliente_id=cliente.id,
        activo=True,
        debe_cambiar_clave=False,
    )
    db.add(cuenta)
    db.flush()

    token, _ = crear_sesion(db, cuenta)
    registrar_auditoria(
        db,
        "registro",
        cuenta_id=cuenta.id,
        detalle=f"Registro de {nombre}",
        ip=ip,
    )
    # Un solo commit: cliente, cuenta, sesión y auditoría se confirman juntos.
    db.commit()
    return SesionSalida(
        token=token,
        rol=cuenta.rol.value,
        cuenta_id=cuenta.id,
        empresa=resumen_empresa(cliente),
        debe_cambiar_clave=cuenta.debe_cambiar_clave,
    )
