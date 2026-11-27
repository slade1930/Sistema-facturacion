import os
from hashlib import md5
from pathlib import Path

from nicegui import app, ui

from components.layout import montar_layout
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
from state.cliente_api import ClienteApi, ErrorApi

app.add_static_files(
    "/static", str(Path(__file__).parent / "static"), max_cache_age=0
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
""",
    shared=True,
)

cliente = ClienteApi()


def probar_salud() -> None:
    try:
        respuesta = cliente.get("/health")
        ui.notify(
            f"Backend disponible: {respuesta.get('status', 'sin estado')}.",
            type="positive",
        )
    except ErrorApi as error:
        ui.notify(f"No se pudo consultar /health: {error.detail}.", type="negative")


@ui.page("/")
def inicio() -> None:
    montar_layout()
    with ui.column().classes("w-full gap-4"):
        with ui.row().classes("orq-acciones gap-2"):
            ui.button(
                "API docs",
                on_click=lambda: ui.navigate.to("http://localhost:8000/docs", new_tab=True),
            ).classes("orq-boton orq-boton--secundario")
        ui.label("Facturación").classes("text-h6")
        ui.label("Interfaz NiceGUI conectada al backend por httpx.").classes(
            "orq-resumen"
        )
        with ui.element("section").classes("orq-ticket w-full max-w-3xl"):
            ui.label("Backend").classes("orq-dato-etiqueta")
            ui.label(cliente.base_url).classes("orq-dato-valor")
            ui.button("Probar /health", on_click=probar_salud).classes(
                "orq-boton orq-boton--primario mt-4"
            )


ui.run(
    host="0.0.0.0",
    port=int(os.getenv("UI_PORT", "8080")),
    title="Sistema de facturación",
)
