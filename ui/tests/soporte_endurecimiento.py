"""Dobles para las pruebas de punta a punta del portal.

La rama de endurecimiento está cortada antes de las etapas B y C: aquí no hay
pantallas ni sesión reales que importar. Este módulo entrega un backend
simulado con datos controlados, un doble de ``state.auth`` y pantallas mínimas
que solo pintan lo que el backend devuelve. No calcula hashes, tokens ni
permisos de negocio: se limita a exponer los datos que la prueba decidió.
"""

from __future__ import annotations

import sys
from itertools import count
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Callable

from nicegui import ui

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state.cliente_api import ErrorApi

TOKEN_ADMIN = "sesion-admin"
SECTORES = {
    "tecnologia": "Tecnología",
    "turismo": "Turismo",
    "supermercado": "Supermercado",
}
PRODUCTOS = (
    {"id": 1, "nombre": "Servidor Orquídea", "precio": "100.00", "sector": "tecnologia", "stock": 5},
    {"id": 2, "nombre": "Paquete turístico", "precio": "50.00", "sector": "turismo", "stock": 5},
    {"id": 3, "nombre": "Cesta de supermercado", "precio": "20.00", "sector": "supermercado", "stock": 5},
    {"id": 4, "nombre": "Artículo sin existencias", "precio": "10.00", "sector": "tecnologia", "stock": 0},
)
UNIDADES_POR_EMPAQUE = {"caja": 4, "media_caja": 2, "unidad": 1}
PDF_SIMULADO = b"%PDF-1.4\n%documento de prueba\n"


def _normalizar(nombre: Any) -> str:
    return " ".join(str(nombre or "").strip().lower().split())


def _importe(valor: float) -> str:
    return f"{valor:.2f}"


class BackendSimulado:
    """Backend de prueba: filtra por el cliente asociado a cada sesión."""

    def __init__(self) -> None:
        self._secuencia = count(1)
        self.empresas: dict[int, dict[str, Any]] = {}
        self.sesiones: dict[str, dict[str, Any]] = {
            TOKEN_ADMIN: {
                "token": TOKEN_ADMIN,
                "rol": "admin",
                "cuenta_id": 0,
                "empresa": {"id": 0, "nombre": "Administración"},
                "activa": True,
            }
        }
        self.carritos: dict[str, list[dict[str, Any]]] = {}
        self.pedidos_registrados: list[dict[str, Any]] = []
        self.facturas: list[dict[str, Any]] = []
        self.movimientos: list[dict[str, Any]] = []
        self.stock = {producto["id"]: producto["stock"] for producto in PRODUCTOS}
        self.llamadas: list[tuple[str, str]] = []

    # ---- Control de la prueba ----

    def sesion_valida(self, token: str | None) -> bool:
        sesion = self.sesiones.get(token or "")
        return bool(sesion and sesion.get("activa", True))

    def expirar(self, token: str | None) -> None:
        if token in self.sesiones:
            self.sesiones[token]["activa"] = False

    def suspender(self, nombre: str) -> None:
        normalizado = _normalizar(nombre)
        for empresa in self.empresas.values():
            if empresa["nombre_normalizado"] == normalizado:
                empresa["estado"] = "suspendida"

    def empresa_por_nombre(self, nombre: str) -> dict[str, Any] | None:
        normalizado = _normalizar(nombre)
        return next(
            (
                empresa
                for empresa in self.empresas.values()
                if empresa["nombre_normalizado"] == normalizado
            ),
            None,
        )

    def _sesion(self, token: str | None) -> dict[str, Any]:
        sesion = self.sesiones.get(token or "")
        if sesion is None or not sesion.get("activa", True):
            raise ErrorApi(401, "La sesión no es válida. Inicia sesión de nuevo.", "UNAUTHORIZED")
        return sesion

    def _respuesta(self, token: str) -> dict[str, Any]:
        sesion = self.sesiones[token]
        return {
            "token": token,
            "rol": sesion["rol"],
            "cuenta_id": sesion["cuenta_id"],
            "empresa": dict(sesion["empresa"]),
            "debe_cambiar_clave": False,
        }

    def get(self, token: str | None, ruta: str, **kwargs: Any) -> Any:
        if ruta == "/api/v1/categorias":
            return self.categorias(token)
        if ruta == "/api/v1/productos":
            return self.productos(token)
        if ruta == "/api/v1/historial":
            return {"items": self.historial(token)}
        if ruta == "/api/v1/pedidos":
            return {"items": self.pedidos_de(token)}
        if ruta == "/api/v1/admin/empresas":
            return self.admin_empresas(token)
        if ruta == "/api/v1/admin/resumen":
            return self.admin_resumen(token)
        if ruta.startswith("/api/v1/facturas/"):
            cola = ruta.removeprefix("/api/v1/facturas/")
            if cola.endswith("/pdf"):
                return self.pdf(token, int(cola.removesuffix("/pdf")))
            return self.factura(token, int(cola))
        raise ErrorApi(404, "Ruta simulada no contemplada.", "NOT_FOUND")

    def post(self, token: str | None, ruta: str, **kwargs: Any) -> Any:
        cuerpo = kwargs.get("json") or {}
        if ruta == "/api/v1/auth/registro":
            return self.registrar(cuerpo)
        if ruta == "/api/v1/auth/login":
            return self.login(cuerpo.get("nombre_empresa"), cuerpo.get("contrasena"))
        if ruta == "/api/v1/carrito/calcular":
            return self.calcular(token, cuerpo.get("lineas") or [])
        if ruta == "/api/v1/compras":
            return self.comprar(
                token, cuerpo.get("lineas") or [], cuerpo.get("clave_idempotencia") or ""
            )
        raise ErrorApi(404, "Ruta simulada no contemplada.", "NOT_FOUND")

    # ---- registro y acceso ----

    def registrar(self, datos: dict[str, Any]) -> dict[str, Any]:
        self.llamadas.append(("POST", "/api/v1/auth/registro"))
        nombre = _normalizar(datos.get("nombre_empresa"))
        sector = str(datos.get("sector") or "")
        if sector not in SECTORES:
            raise ErrorApi(422, "El sector indicado no es válido.", "VALIDATION_ERROR")
        if self.empresa_por_nombre(nombre) is not None:
            raise ErrorApi(409, "Ya existe una empresa con ese nombre.", "CONFLICT")
        cuenta_id = next(self._secuencia)
        token = f"sesion-{cuenta_id}"
        empresa = {
            "id": cuenta_id,
            "cliente_id": cuenta_id,
            "nombre": str(datos.get("nombre_empresa") or "").strip(),
            "nombre_normalizado": nombre,
            "ruc": str(datos.get("ruc") or ""),
            "sector": sector,
            "estado": "activo",
        }
        self.empresas[cuenta_id] = empresa
        self.sesiones[token] = {
            "token": token,
            "rol": "empresa",
            "cuenta_id": cuenta_id,
            "empresa": empresa,
            "activa": True,
        }
        return self._respuesta(token)

    def login(self, nombre: str, valor: str) -> dict[str, Any]:
        self.llamadas.append(("POST", "/api/v1/auth/login"))
        empresa = self.empresa_por_nombre(nombre)
        if empresa is None or not valor:
            raise ErrorApi(401, "Empresa o contraseña incorrectos.", "UNAUTHORIZED")
        if empresa["estado"] == "suspendida":
            raise ErrorApi(403, "Esta empresa está suspendida.", "FORBIDDEN")
        token = next(
            (
                llave
                for llave, sesion in self.sesiones.items()
                if sesion["rol"] == "empresa" and sesion["cuenta_id"] == empresa["id"]
            ),
            None,
        )
        if token is None or not self.sesion_valida(token):
            raise ErrorApi(401, "La sesión expiró. Inicia sesión de nuevo.", "UNAUTHORIZED")
        return self._respuesta(token)

    # ---- catálogo, compra y documentos ----

    def categorias(self, token: str | None) -> list[dict[str, Any]]:
        self.llamadas.append(("GET", "/api/v1/categorias"))
        sesion = self._sesion(token)
        sectores = (
            list(SECTORES)
            if sesion["rol"] == "admin"
            else [sesion["empresa"]["sector"]]
        )
        return [
            {"id": indice, "nombre": SECTORES[sector], "sector": sector}
            for indice, sector in enumerate(sectores, start=1)
        ]

    def productos(self, token: str | None) -> list[dict[str, Any]]:
        self.llamadas.append(("GET", "/api/v1/productos"))
        sesion = self._sesion(token)
        if sesion["rol"] == "admin":
            return [dict(producto) for producto in PRODUCTOS]
        sector = sesion["empresa"]["sector"]
        return [dict(producto) for producto in PRODUCTOS if producto["sector"] == sector]

    def carrito(self, token: str | None) -> list[dict[str, Any]]:
        self._sesion(token)
        return self.carritos.setdefault(token or "", [])

    def anadir(self, token: str | None, producto: dict[str, Any]) -> None:
        self.carrito(token).append(
            {
                "producto_id": producto["id"],
                "nombre": producto["nombre"],
                "tipo_empaque": "caja",
                "cantidad": 1,
            }
        )

    def vaciar_carrito(self, token: str | None) -> None:
        self.carritos[token or ""] = []

    def calcular(self, token: str | None, lineas: list[dict[str, Any]]) -> dict[str, Any]:
        self.llamadas.append(("POST", "/api/v1/carrito/calcular"))
        self._sesion(token)
        calculadas = []
        total = 0.0
        for linea in lineas:
            producto = self._producto(linea["producto_id"])
            unidades = float(linea["cantidad"]) * UNIDADES_POR_EMPAQUE[linea["tipo_empaque"]]
            subtotal = float(producto["precio"]) * unidades
            total += subtotal
            calculadas.append(
                {
                    "descripcion": producto["nombre"],
                    "tipo_empaque": linea["tipo_empaque"],
                    "cantidad": str(linea["cantidad"]),
                    "subtotal": _importe(subtotal),
                }
            )
        return {"lineas": calculadas, "total": _importe(total)}

    def comprar(
        self, token: str | None, lineas: list[dict[str, Any]], idempotencia: str
    ) -> dict[str, Any]:
        self.llamadas.append(("POST", "/api/v1/compras"))
        sesion = self._sesion(token)
        if sesion["rol"] != "empresa":
            raise ErrorApi(403, "El administrador no compra en el portal.", "FORBIDDEN")
        totales = self.calcular(token, lineas)
        # La comprobación completa va antes de cualquier cambio: si falla, no hay pedido,
        # factura ni movimiento de inventario.
        for linea in lineas:
            producto = self._producto(linea["producto_id"])
            unidades = float(linea["cantidad"]) * UNIDADES_POR_EMPAQUE[linea["tipo_empaque"]]
            if self.stock[producto["id"]] < unidades:
                raise ErrorApi(409, f"Stock insuficiente para {producto['nombre']}.", "CONFLICT")
        pedido_id = next(self._secuencia)
        factura_id = next(self._secuencia)
        for linea in lineas:
            producto = self._producto(linea["producto_id"])
            unidades = float(linea["cantidad"]) * UNIDADES_POR_EMPAQUE[linea["tipo_empaque"]]
            self.stock[producto["id"]] -= unidades
            self.movimientos.append(
                {"producto_id": producto["id"], "cantidad": unidades, "factura_id": factura_id}
            )
        numero_serie = f"FAC-2026-{factura_id:04d}"
        self.pedidos_registrados.append(
            {
                "id": pedido_id,
                "cliente_id": sesion["empresa"]["id"],
                "factura_generada_id": factura_id,
            }
        )
        self.facturas.append(
            {
                "id": factura_id,
                "numero_serie": numero_serie,
                "cliente_id": sesion["empresa"]["id"],
                "cliente_nombre": sesion["empresa"]["nombre"],
                "total": totales["total"],
                "estado": "emitida",
                "idempotencia": idempotencia,
            }
        )
        return {
            "pedido_id": pedido_id,
            "factura_id": factura_id,
            "numero_serie": numero_serie,
            "total": totales["total"],
            "reutilizada": False,
        }

    def _producto(self, producto_id: int) -> dict[str, Any]:
        producto = next((item for item in PRODUCTOS if item["id"] == producto_id), None)
        if producto is None:
            raise ErrorApi(404, "Producto no encontrado.", "NOT_FOUND")
        return producto

    def historial(self, token: str | None) -> list[dict[str, Any]]:
        self.llamadas.append(("GET", "/api/v1/historial"))
        sesion = self._sesion(token)
        if sesion["rol"] == "admin":
            return [dict(factura) for factura in self.facturas]
        cliente_id = sesion["empresa"]["id"]
        return [dict(factura) for factura in self.facturas if factura["cliente_id"] == cliente_id]

    def pedidos_de(self, token: str | None) -> list[dict[str, Any]]:
        self.llamadas.append(("GET", "/api/v1/pedidos"))
        sesion = self._sesion(token)
        if sesion["rol"] == "admin":
            return [dict(pedido) for pedido in self.pedidos_registrados]
        cliente_id = sesion["empresa"]["id"]
        return [
            dict(pedido)
            for pedido in self.pedidos_registrados
            if pedido["cliente_id"] == cliente_id
        ]

    def factura(self, token: str | None, factura_id: int) -> dict[str, Any]:
        self.llamadas.append(("GET", f"/api/v1/facturas/{factura_id}"))
        sesion = self._sesion(token)
        factura = next((item for item in self.facturas if item["id"] == factura_id), None)
        if factura is None or (
            sesion["rol"] != "admin" and factura["cliente_id"] != sesion["empresa"]["id"]
        ):
            raise ErrorApi(404, "Factura no encontrada.", "NOT_FOUND")
        return dict(factura)

    def pdf(self, token: str | None, factura_id: int) -> bytes:
        self.llamadas.append(("GET", f"/api/v1/facturas/{factura_id}/pdf"))
        factura = self.factura(token, factura_id)
        return PDF_SIMULADO + f"Serie {factura['numero_serie']}\n".encode("utf-8")

    def admin_empresas(self, token: str | None) -> list[dict[str, Any]]:
        self.llamadas.append(("GET", "/api/v1/admin/empresas"))
        sesion = self._sesion(token)
        if sesion["rol"] != "admin":
            raise ErrorApi(403, "Esta consulta es solo para administradores.", "FORBIDDEN")
        return [
            {
                "id": empresa["id"],
                "nombre": empresa["nombre"],
                "ruc": empresa["ruc"],
                "sector": empresa["sector"],
                "estado": empresa["estado"],
            }
            for empresa in self.empresas.values()
        ]

    def admin_resumen(self, token: str | None) -> dict[str, Any]:
        self.llamadas.append(("GET", "/api/v1/admin/resumen"))
        sesion = self._sesion(token)
        if sesion["rol"] != "admin":
            raise ErrorApi(403, "Esta consulta es solo para administradores.", "FORBIDDEN")
        total = sum(float(factura["total"]) for factura in self.facturas)
        return {
            "empresas": len(self.empresas),
            "pedidos": len(self.pedidos_registrados),
            "facturas": len(self.facturas),
            "facturado": _importe(total),
        }


class AuthDoble:
    """Doble de ``state.auth``: solo guarda lo que entregó el backend simulado."""

    def __init__(self, backend: BackendSimulado) -> None:
        self.backend = backend
        self.estado: dict[str, Any] = {}

    async def conectar(self) -> None:
        return None

    def token(self) -> str | None:
        valor = self.estado.get("token")
        return str(valor) if valor else None

    def datos_usuario(self) -> dict[str, Any]:
        return dict(self.estado.get("usuario") or {})

    def guardar_sesion(self, respuesta: dict[str, Any]) -> None:
        self.estado["token"] = respuesta.get("token")
        self.estado["usuario"] = {
            "rol": respuesta.get("rol"),
            "cuenta_id": respuesta.get("cuenta_id"),
            "empresa": dict(respuesta.get("empresa") or {}),
        }

    def cerrar_sesion(self) -> None:
        self.estado.clear()

    def cliente_portal(self) -> "AuthDoble":
        return self

    def get(self, ruta: str, **kwargs: Any) -> Any:
        return self.backend.get(self.token(), ruta, **kwargs)

    def post(self, ruta: str, **kwargs: Any) -> Any:
        return self.backend.post(self.token(), ruta, **kwargs)

    def exigir_sesion(self) -> bool:
        if self.token() and self.backend.sesion_valida(self.token()):
            return True
        ui.label("Inicia sesión para entrar al portal.")
        ui.link("Ir a iniciar sesión", "/login")
        ui.navigate.to("/login")
        return False

    def es_empresa(self) -> bool:
        return self.datos_usuario().get("rol") == "empresa"

    def nombre_empresa(self) -> str:
        return str((self.datos_usuario().get("empresa") or {}).get("nombre") or "")


def instalar_dobles(monkeypatch: Any, backend: BackendSimulado) -> SimpleNamespace:
    """Inyecta sesión y guardianes controlados sin tocar los archivos de B o C."""
    destinos: list[str] = []
    monkeypatch.setattr(ui.navigate, "to", destinos.append)

    auth = AuthDoble(backend)
    modulo_auth = ModuleType("state.auth")
    for nombre in (
        "token",
        "datos_usuario",
        "guardar_sesion",
        "cerrar_sesion",
        "cliente_portal",
        "exigir_sesion",
        "conectar",
        "es_empresa",
        "nombre_empresa",
    ):
        setattr(modulo_auth, nombre, getattr(auth, nombre))
    modulo_auth.CLAVE_TOKEN = "sesion-portal"
    monkeypatch.setitem(sys.modules, "state.auth", modulo_auth)
    import state

    monkeypatch.setattr(state, "auth", modulo_auth, raising=False)

    def exigir_admin() -> bool:
        datos = auth.datos_usuario()
        if datos.get("rol") == "admin" and backend.sesion_valida(auth.token()):
            return True
        ui.label("Inicia sesión para entrar al portal.")
        ui.link("Ir a iniciar sesión", "/login")
        ui.navigate.to("/login")
        return False

    modulo_seguridad = ModuleType("components.admin.seguridad")
    modulo_seguridad.exigir_admin = exigir_admin
    paquete_admin = ModuleType("components.admin")
    paquete_admin.__path__ = []
    paquete_admin.seguridad = modulo_seguridad
    monkeypatch.setitem(sys.modules, "components.admin", paquete_admin)
    monkeypatch.setitem(sys.modules, "components.admin.seguridad", modulo_seguridad)
    import components

    monkeypatch.setattr(components, "admin", paquete_admin, raising=False)
    return SimpleNamespace(backend=backend, auth=auth, destinos=destinos)


# ---------------------------------------------------------------------------
# Pantallas dobles: solo muestran lo que devolvió el backend simulado.
# ---------------------------------------------------------------------------


def pagina_registro(backend: BackendSimulado, auth: AuthDoble) -> Callable[[], None]:
    def pagina() -> None:
        ui.label("Crear empresa")
        campos = {
            "nombre_empresa": ui.input(label="Nombre de la empresa"),
            "ruc": ui.input(label="RUC"),
            "correo": ui.input(label="Correo electrónico"),
            "direccion": ui.input(label="Dirección"),
            "telefono": ui.input(label="Teléfono"),
            "sucursal": ui.input(label="Sucursal"),
            "contrasena": ui.input(label="Contraseña"),
            "sector": ui.select(SECTORES, label="Sector", value="tecnologia"),
        }
        mensajes = ui.column()

        def crear() -> None:
            mensajes.clear()
            datos = {clave: campo.value for clave, campo in campos.items()}
            try:
                respuesta = backend.registrar(datos)
            except ErrorApi as error:
                with mensajes:
                    ui.label(error.detail)
                return
            auth.guardar_sesion(respuesta)
            with mensajes:
                ui.label("Empresa creada. Bienvenida a tu portal.")
            ui.navigate.to("/portal/inicio")

        ui.button("Crear empresa", on_click=crear)

    return pagina


def pagina_login(backend: BackendSimulado, auth: AuthDoble) -> Callable[[], None]:
    def pagina() -> None:
        ui.label("Entrar al portal")
        empresa = ui.input(label="Empresa")
        valor = ui.input(label="Contraseña")
        mensajes = ui.column()

        def entrar() -> None:
            mensajes.clear()
            try:
                respuesta = backend.login(empresa.value or "", valor.value or "")
            except ErrorApi as error:
                with mensajes:
                    ui.label(error.detail)
                return
            auth.guardar_sesion(respuesta)
            with mensajes:
                ui.label("Sesión iniciada.")
            ui.navigate.to("/portal/inicio")

        ui.button("Entrar", on_click=entrar)

    return pagina


def pagina_catalogo(backend: BackendSimulado, auth: AuthDoble) -> Callable[[], None]:
    def pagina() -> None:
        if not auth.exigir_sesion():
            return
        ui.label("Catálogo de mi sector")
        for producto in backend.productos(auth.token()):
            with ui.element("article"):
                ui.label(producto["nombre"])
                ui.button(
                    f"Añadir {producto['nombre']}",
                    on_click=lambda p=producto: backend.anadir(auth.token(), p),
                )

    return pagina


def pagina_carrito(backend: BackendSimulado, auth: AuthDoble) -> Callable[[], None]:
    def pagina() -> None:
        if not auth.exigir_sesion():
            return
        carrito = backend.carrito(auth.token())
        ui.label("Mi carrito")
        for linea in carrito:
            ui.label(linea["nombre"])
        mensajes = ui.column()

        def confirmar() -> None:
            mensajes.clear()
            try:
                respuesta = backend.comprar(auth.token(), carrito, "idempotencia-controlada")
            except ErrorApi as error:
                with mensajes:
                    ui.label(error.detail)
                return
            backend.vaciar_carrito(auth.token())
            with mensajes:
                ui.label("Compra confirmada. Tu factura ya está lista.")
            ui.navigate.to(f"/portal/compra-exitosa?factura_id={respuesta['factura_id']}")

        ui.button("Confirmar compra", on_click=confirmar)

    return pagina


def pagina_compra_exitosa(
    backend: BackendSimulado, auth: AuthDoble, factura_id: int
) -> Callable[[], None]:
    def pagina() -> None:
        if not auth.exigir_sesion():
            return
        factura = backend.factura(auth.token(), factura_id)
        ui.label("Tu compra quedó registrada")
        ui.label(factura["numero_serie"])
        ui.link("Ver factura", "/portal/factura-detalle")

    return pagina


def pagina_facturas(backend: BackendSimulado, auth: AuthDoble) -> Callable[[], None]:
    def pagina() -> None:
        if not auth.exigir_sesion():
            return
        ui.label("Mis facturas")
        for factura in backend.historial(auth.token()):
            ui.label(factura["numero_serie"])

    return pagina


def pagina_factura_detalle(
    backend: BackendSimulado, auth: AuthDoble, factura_id: int
) -> Callable[[], None]:
    def pagina() -> None:
        if not auth.exigir_sesion():
            return
        try:
            factura = backend.factura(auth.token(), factura_id)
        except ErrorApi as error:
            ui.label(error.detail)
            return
        ui.label(factura["numero_serie"])
        mensajes = ui.column()

        def descargar() -> None:
            contenido = backend.pdf(auth.token(), factura_id)
            mensajes.clear()
            with mensajes:
                ui.label(f"PDF disponible ({len(contenido)} bytes)")

        ui.button("Descargar PDF", on_click=descargar)

    return pagina


def pagina_admin(backend: BackendSimulado, auth: AuthDoble, ruta: str) -> Callable[[], None]:
    def pagina() -> None:
        from components.admin import seguridad

        if not seguridad.exigir_admin():
            return
        ui.label(f"Panel del administrador: {ruta}")
        for empresa in backend.admin_empresas(auth.token()):
            ui.label(empresa["nombre"])
        resumen = backend.admin_resumen(auth.token())
        ui.label(f"Empresas: {resumen['empresas']}")
        ui.label(f"Total facturado: {resumen['facturado']}")

    return pagina


def pagina_empresa_privada(auth: AuthDoble) -> Callable[[], None]:
    def pagina() -> None:
        if not auth.exigir_sesion():
            return
        ui.label("Zona de la empresa")

    return pagina
