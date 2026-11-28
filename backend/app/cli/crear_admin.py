"""Crea el primer administrador desde la consola. Sistema; etapa A."""

import argparse
import getpass
import os
import sys

from app.db.session import get_session_local
from app.models.seguridad import Cuenta, RolCuenta
from app.repositories.cuentas import CuentasRepository
from app.services.auth import (
    hash_clave,
    normalizar_nombre_usuario,
    registrar_auditoria,
    validar_politica_clave,
)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Crea una cuenta de administrador del portal."
    )
    analizador.add_argument("--usuario", required=True, help="Nombre de usuario único")
    argumentos = analizador.parse_args(argv)

    contrasena = os.getenv("ADMIN_PASSWORD") or getpass.getpass(
        "Contraseña del administrador: "
    )
    try:
        validar_politica_clave(contrasena)
    except ValueError as exc:
        print(f"No se pudo crear el administrador: {exc}", file=sys.stderr)
        return 2

    db = get_session_local()()
    try:
        nombre = normalizar_nombre_usuario(argumentos.usuario)
        if CuentasRepository(db).por_nombre_usuario(nombre) is not None:
            print("Ya existe una cuenta con ese nombre.", file=sys.stderr)
            return 3
        cuenta = Cuenta(
            nombre_usuario=nombre,
            password_hash=hash_clave(contrasena),
            rol=RolCuenta.ADMIN,
            cliente_id=None,
            activo=True,
            debe_cambiar_clave=True,
        )
        db.add(cuenta)
        db.flush()
        registrar_auditoria(
            db, "registro_admin", cuenta_id=cuenta.id, detalle=f"Alta de {nombre}"
        )
        db.commit()
    finally:
        db.close()

    print(f"Administrador creado: {nombre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
