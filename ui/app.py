import os
from hashlib import md5, sha256
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx
from fastapi import Response
from nicegui import app, ui

from components.forms import boton_orquidea, campo_orquidea, mostrar_error
from components.layout import datos_negocio, montar_layout
from components.shared import estado_cargando, estado_vacio, sello_estado, tabla_orquidea
from pages.catalogo import carrito as _pagina_carrito
from pages.catalogo import catalogo as _pagina_catalogo
from pages.facturacion import configuracion as _pagina_configuracion
from pages.facturacion import detalle as _pagina_detalle
from pages.facturacion import historial as _pagina_historial
from pages.facturacion import nueva as _pagina_nueva
from pages.pedidos import convertir_a_factura as _pagina_convertir
from pages.pedidos import detalle_pedido as _pagina_detalle_pedido
from pages.pedidos import formulario_pedido as _pagina_formulario
from pages.pedidos import pedido_exitoso as _pagina_exitoso
from pages.pedidos import pedidos_pendientes as _pagina_pedidos
from pages.verificar import verificar as _pagina_verificar
from state.cliente_api import ClienteApi

app.add_static_files(
    "/static", str(Path(__file__).parent / "static"), max_cache_age=0
)


@app.get("/media/{nombre}")
def servir_logo(nombre: str) -> Response:
    """Muestra el logo guardado por el backend sin exponer su dirección interna."""
    if not nombre or "/" in nombre or "\\" in nombre or ".." in nombre:
        return Response(status_code=404)
    base = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    try:
        with httpx.Client(timeout=5.0) as cliente:
            respuesta = cliente.get(f"{base}/media/{quote(nombre)}")
    except Exception:
        return Response(status_code=502)
    return Response(
        content=respuesta.content,
        status_code=respuesta.status_code,
        media_type=respuesta.headers.get("content-type", "application/octet-stream"),
    )


app.colors(
    primary="#6C2BD9",
    secondary="#220A3A",
    accent="#D4157F",
    positive="#145C45",
    negative="#9C1B2E",
    warning="#7A4A00",
    info="#6C2BD9",
    dark="#220A3A",
)
CSS = Path(__file__).parent / "static" / "orquidea.css"
VERSION = md5(CSS.read_bytes()).hexdigest()[:8]
ui.add_head_html(
    f'<link rel="stylesheet" href="/static/orquidea.css?v={VERSION}">', shared=True
)
ui.add_head_html(
    """
<script>
  try {
    if (!sessionStorage.getItem('orq_entrada')) {
      document.documentElement.classList.add('orq-entrada');
      sessionStorage.setItem('orq_entrada', '1');
    }
  } catch (error) { /* sin sessionStorage: sin animación de entrada */ }
</script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    var numero = '';
    try { numero = sessionStorage.getItem('orq_carrito_count') || ''; } catch (error) { numero = ''; }
    document.querySelectorAll('.orq-contador-carrito').forEach(function (elemento) {
      elemento.textContent = numero === '0' ? '' : numero;
    });
  });
</script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    function contar(elemento) {
      if (elemento.dataset.orqContado) return;
      elemento.dataset.orqContado = '1';
      const valor = elemento.dataset.valor || elemento.textContent.trim();
      const partes = valor.match(/^([^0-9-]*)(-?[0-9][0-9.,]*)(.*)$/);
      if (!partes) return;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const prefijo = partes[1];
      const textoNumero = partes[2];
      const sufijo = partes[3];
      const separador = textoNumero.includes('.') ? '.' : (textoNumero.includes(',') ? ',' : '');
      const decimales = separador ? textoNumero.split(separador).pop().length : 0;
      const objetivo = Number(textoNumero.replace(/[.,]/g, function (caracter) {
        return caracter === separador ? '.' : '';
      }));
      if (!Number.isFinite(objetivo)) return;
      const inicio = performance.now();
      function paso(ahora) {
        const progreso = Math.min(1, (ahora - inicio) / 520);
        const actual = objetivo * (1 - Math.pow(1 - progreso, 3));
        elemento.textContent = prefijo + actual.toFixed(decimales).replace('.', separador || '.') + sufijo;
        if (progreso < 1) requestAnimationFrame(paso);
        else elemento.textContent = valor;
      }
      requestAnimationFrame(paso);
    }
    document.querySelectorAll('.orq-total').forEach(contar);
    const observador = new MutationObserver(function (cambios) {
      cambios.forEach(function (cambio) {
        cambio.addedNodes.forEach(function (nodo) {
          if (nodo.nodeType !== 1) return;
          if (nodo.classList.contains('orq-total')) contar(nodo);
          nodo.querySelectorAll('.orq-total').forEach(contar);
        });
      });
    });
    observador.observe(document.body, { childList: true, subtree: true });
  });
</script>
<script>
  (function () {
    function cerrarSubmenus() {
      document.querySelectorAll('.orq-menu-boton[aria-expanded="true"]').forEach(function (boton) {
        boton.setAttribute('aria-expanded', 'false');
        var submenu = document.getElementById(boton.getAttribute('aria-controls'));
        if (submenu) submenu.hidden = true;
      });
    }
    function cerrarCajon() {
      var boton = document.querySelector('.orq-hamburguesa');
      var cajon = document.getElementById('orq-cajon');
      if (boton) boton.setAttribute('aria-expanded', 'false');
      if (cajon) cajon.hidden = true;
    }
    document.addEventListener('click', function (evento) {
      var boton = evento.target.closest('.orq-menu-boton');
      if (boton) {
        var abierto = boton.getAttribute('aria-expanded') === 'true';
        cerrarSubmenus();
        if (!abierto) {
          var submenu = document.getElementById(boton.getAttribute('aria-controls'));
          boton.setAttribute('aria-expanded', 'true');
          if (submenu) submenu.hidden = false;
        }
        evento.stopPropagation();
        return;
      }
      var hamburguesa = evento.target.closest('.orq-hamburguesa');
      if (hamburguesa) {
        var abiertoCajon = hamburguesa.getAttribute('aria-expanded') === 'true';
        cerrarSubmenus();
        var cajon = document.getElementById('orq-cajon');
        hamburguesa.setAttribute('aria-expanded', abiertoCajon ? 'false' : 'true');
        if (cajon) cajon.hidden = abiertoCajon;
        evento.stopPropagation();
        return;
      }
      if (evento.target.closest('#orq-cajon a')) cerrarCajon();
      if (!evento.target.closest('.orq-submenu')) cerrarSubmenus();
    });
    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape') {
        cerrarSubmenus();
        cerrarCajon();
        return;
      }
      if (evento.key === 'ArrowDown' && evento.target.matches('.orq-menu-boton')) {
        var submenu = document.getElementById(evento.target.getAttribute('aria-controls'));
        if (submenu && submenu.hidden) evento.target.click();
        if (submenu) {
          var primerEnlace = submenu.querySelector('a');
          if (primerEnlace) primerEnlace.focus();
        }
        evento.preventDefault();
      }
    });
  })();
</script>
""",
    shared=True,
)

cliente = ClienteApi()


def _obtener_historial(limite: int = 5) -> list[dict]:
    respuesta = cliente.get("/api/v1/historial", params={"limite": limite})
    return list(respuesta.get("items") or [])


def _obtener_pedidos_por_facturar() -> list[dict] | None:
    try:
        return list(
            cliente.get("/api/v1/pedidos/por-facturar", params={"limite": 500})
        )
    except Exception:
        return None


def _ticket_ultima(factura: dict) -> None:
    with ui.element("section").classes("orq-ticket w-full"):
        with ui.row().classes("orq-ticket-cabecera w-full"):
            with ui.column().classes("gap-0"):
                ui.label(str(factura.get("numero_serie") or "")).classes(
                    "orq-ticket-folio"
                )
                ui.label(f"Fecha {factura.get('fecha') or ''}").classes(
                    "orq-ticket-fecha"
                )
            sello_estado(str(factura.get("estado") or ""))
        with ui.column().classes("orq-ticket-datos w-full"):
            with ui.element("div").classes("orq-dato"):
                ui.label("Cliente").classes("orq-dato-etiqueta")
                ui.label(str(factura.get("cliente_nombre") or "")).classes(
                    "orq-dato-valor"
                )
            with ui.element("div").classes("orq-dato"):
                ui.label("RUC").classes("orq-dato-etiqueta")
                ui.label(str(factura.get("cliente_ruc") or "")).classes(
                    "orq-dato-valor"
                )
        with ui.column().classes("orq-ticket-totales"):
            ui.html(
                '<div class="orq-dato"><span class="orq-dato-etiqueta">Total</span>'
                '<span class="orq-total" data-valor="'
                + str(factura.get("total") or "0.00")
                + '">'
                + str(factura.get("total") or "0.00")
                + "</span></div>"
            )
        with ui.row().classes("orq-ticket-acciones w-full"):
            ui.link(
                "Ver factura",
                f"/facturacion/detalle?factura_id={factura.get('id') or ''}",
            ).classes("orq-boton orq-boton--texto")


@ui.page("/")
def inicio() -> None:
    montar_layout()

    with ui.element("section").classes("orq-hero w-full"):
        ui.label("Tu facturación, en orden").classes("orq-hero-titulo")
        ui.label(
            "Elige una acción, revisa lo emitido o comprueba una factura."
        ).classes("orq-hero-bajada")
        with ui.column().classes("orq-hero-ultima w-full") as ultima:
            estado_cargando(3)

    try:
        facturas = _obtener_historial(5)
    except Exception as error:
        ultima.clear()
        mostrar_error(ultima, error)
        facturas = []
    else:
        ultima.clear()
        with ultima:
            if facturas:
                ui.label("Última factura emitida").classes("orq-bloque-ayuda")
                _ticket_ultima(facturas[0])
            else:
                estado_vacio(
                    "Todavía no emitiste facturas.",
                    "Cuando emitas una, aparece acá.",
                )

    with ui.element("section").classes("orq-bloque w-full"):
        ui.label("¿Qué quieres hacer?").classes("orq-bloque-titulo")
        ui.label("Entradas directas a las tareas del negocio.").classes(
            "orq-bloque-ayuda"
        )
        entradas = (
            ("01", "Emitir una factura", "Facturación", "/facturacion/nueva"),
            ("02", "Revisar las emitidas", "Facturación", "/facturacion/historial"),
            ("03", "Armar un pedido", "Pedidos", "/pedidos/formulario"),
            ("04", "Ver productos", "Catálogo", "/catalogo"),
            ("05", "Comprobar una factura", "Consultar", "/verificar"),
        )
        with ui.column().classes("orq-entradas w-full"):
            for numero, texto, seccion, ruta in entradas:
                with ui.link("", ruta).classes("orq-entrada") as enlace:
                    ui.label(numero).classes("orq-entrada-numero")
                    ui.label(texto).classes("orq-entrada-titulo")
                    ui.label(seccion).classes("orq-entrada-seccion")
                enlace.props(f'aria-label="{texto}"')

    with ui.element("section").classes("orq-bloque w-full"):
        ui.label("Cómo funciona").classes("orq-bloque-titulo")
        ui.label("Del pedido a la verificación, sin pasos ocultos.").classes(
            "orq-bloque-ayuda"
        )
        pasos = (
            ("01", "Pedido", "Elige los productos y confirma la entrega."),
            ("02", "Factura", "Emite el talonario con cliente, líneas e ITBMS."),
            ("03", "QR", "La factura queda lista para compartir con su código."),
            ("04", "Verificación", "Cualquiera puede comprobar los datos con serie y código."),
        )
        with ui.row().classes("orq-pasos w-full"):
            for numero, titulo, texto in pasos:
                with ui.column().classes("orq-paso"):
                    ui.label(numero).classes("orq-paso-numero")
                    ui.label(titulo).classes("orq-paso-titulo")
                    ui.label(texto).classes("orq-paso-texto")

    with ui.element("section").classes("orq-bloque w-full"):
        ui.label("Actividad reciente").classes("orq-bloque-titulo")
        pedidos = _obtener_pedidos_por_facturar()
        if pedidos is not None:
            ui.label(f"Pedidos por facturar: {len(pedidos)}").classes(
                "orq-aviso-pedidos"
            )
        with ui.column().classes("w-full") as actividad:
            estado_cargando(5)
        actividad.clear()
        with actividad:
            if facturas:
                columnas = [
                    {
                        "name": "numero_serie",
                        "label": "Número",
                        "field": "numero_serie",
                        "align": "left",
                    },
                    {"name": "fecha", "label": "Fecha", "field": "fecha", "align": "left"},
                    {
                        "name": "cliente_nombre",
                        "label": "Cliente",
                        "field": "cliente_nombre",
                        "align": "left",
                    },
                    {
                        "name": "total",
                        "label": "Total",
                        "field": "total",
                        "align": "right",
                    },
                    {
                        "name": "estado",
                        "label": "Estado",
                        "field": "estado",
                        "align": "left",
                    },
                ]
                tabla_orquidea(columnas, facturas, row_key="numero_serie")
            else:
                estado_vacio("No hay actividad para mostrar.")

    with ui.element("section").classes("orq-bloque w-full"):
        ui.label("Verificación pública").classes("orq-bloque-titulo")
        ui.label(
            "Ingresa los datos impresos en la factura para comprobarla."
        ).classes("orq-bloque-ayuda")
        with ui.element("div").classes("orq-verificar-bloque"):
            with ui.column().classes("orq-verificar-campos w-full"):
                serie = campo_orquidea(
                    "Número de serie", placeholder="FAC-2026-0001"
                )
                codigo = campo_orquidea(
                    "Código de verificación", placeholder="El que aparece en la factura"
                )

            def verificar_desde_inicio() -> None:
                if not str(serie.value or "").strip() or not str(
                    codigo.value or ""
                ).strip():
                    ui.notify(
                        "Ingresa el número de serie y el código de verificación.",
                        type="warning",
                    )
                    return
                consulta = urlencode(
                    {
                        "numero_serie": str(serie.value).strip(),
                        "codigo": str(codigo.value).strip(),
                    }
                )
                ui.navigate.to(f"/verificar?{consulta}")

            boton_orquidea("Verificar", verificar_desde_inicio)

    negocio = datos_negocio()
    partes = []
    if negocio.get("nombre"):
        partes.append(negocio["nombre"])
    if negocio.get("ruc"):
        partes.append(f"RUC {negocio['ruc']}")
    if partes:
        ui.label(" · ".join(partes)).classes("orq-pie")


# Registro de rutas del administrador (etapa C2): solo imports, sin tocar el
# comportamiento existente ni la configuración de la aplicación.
from pages.admin import auditoria as _pagina_admin_auditoria  # noqa: E402
from pages.admin import catalogo as _pagina_admin_catalogo  # noqa: E402
from pages.admin import empresas as _pagina_admin_empresas  # noqa: E402
from pages.admin import inventario as _pagina_admin_inventario  # noqa: E402
from pages.admin import panel as _pagina_admin_panel  # noqa: E402
from pages.admin import pedidos as _pagina_admin_pedidos  # noqa: E402
from pages.admin import por_facturar as _pagina_admin_por_facturar  # noqa: E402


ui.run(
    host="0.0.0.0",
    port=int(os.getenv("UI_PORT", "8080")),
    title="Orquídea",
    # El carrito vive en el almacenamiento de la pestaña; derivamos la clave de sesión
    # de la API_KEY que ya existe, sin pedir una variable nueva.
    storage_secret=sha256(
        os.getenv("API_KEY", "orquidea-local").encode("utf-8")
    ).hexdigest(),
)
