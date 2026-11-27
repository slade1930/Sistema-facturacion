"""LSTM del pronóstico de ventas (PyTorch CPU, sin descargas).

Las importaciones de torch son diferidas: este módulo se puede importar
en cualquier entorno sin PyTorch instalado. Sin modelo entrenado,
predecir() devuelve None ("sin evaluar").
"""
from __future__ import annotations

from pathlib import Path

NOMBRE_MODELO = "pronostico_lstm"
ARCHIVO_MODELO = "pronostico_lstm.pt"
VENTANA = 12      # meses de historia que mira el LSTM
HORIZONTE = 6     # meses que pronostica de una vez
MODELOS_DIR = Path(__file__).resolve().parents[3] / "ml_models"


def preparar_ventanas(serie, ventana=VENTANA, horizonte=HORIZONTE):
    """Convierte la serie en pares (ventana -> horizonte).

    Devuelve (X, Y): X[i] son `ventana` valores, Y[i] los `horizonte`
    valores siguientes. Solostdlib: listas de floats.
    """
    y = [float(v) for v in serie]
    if len(y) < ventana + horizonte:
        raise ValueError(
            f"serie muy corta: {len(y)} puntos, mínimo {ventana + horizonte}"
        )
    X, Y = [], []
    ultimo = len(y) - ventana - horizonte + 1
    for i in range(ultimo):
        X.append(y[i:i + ventana])
        Y.append(y[i + ventana:i + ventana + horizonte])
    return X, Y


def _media_desv(serie):
    n = len(serie)
    media = sum(serie) / n
    var = sum((v - media) ** 2 for v in serie) / n
    return media, max(var ** 0.5, 1e-6)


def _normalizar(serie, media, desv):
    return [(v - media) / desv for v in serie]


def _desnormalizar(serie, media, desv):
    return [v * desv + media for v in serie]


def _construir_red(ventana, horizonte, ocultos=16):
    """LSTM simple: ventana -> hidden -> horizonte salidas."""
    import torch
    from torch import nn

    class _Red(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=1, hidden_size=ocultos,
                num_layers=1, batch_first=True,
            )
            self.cabeza = nn.Linear(ocultos, horizonte)

        def forward(self, x):
            # x: (batch, ventana, 1)
            salida, _ = self.lstm(x)
            return self.cabeza(salida[:, -1, :])

    return _Red()


def entrenar_lstm(serie, horizonte=HORIZONTE, ventana=VENTANA,
                  epocas=80, semilla=20261126, lr=0.01):
    """Entrena la LSTM en CPU. Devuelve artefacto para torch.save."""
    import torch

    torch.manual_seed(semilla)
    X, Y = preparar_ventanas(serie, ventana, horizonte)
    aplanada = [v for fila in X for v in fila]
    media, desv = _media_desv(aplanada + [v for fila in Y for v in fila])

    Xn = torch.tensor(
        [[[v] for v in _normalizar(fila, media, desv)] for fila in X],
        dtype=torch.float32,
    )
    Yn = torch.tensor(
        [[(v - media) / desv for v in fila] for fila in Y],
        dtype=torch.float32,
    )

    red = _construir_red(ventana, horizonte)
    optimizador = torch.optim.Adam(red.parameters(), lr=lr)
    perdida_fn = torch.nn.MSELoss()
    red.train()
    for _ in range(int(epocas)):
        optimizador.zero_grad()
        perdida = perdida_fn(red(Xn), Yn)
        perdida.backward()
        optimizador.step()

    return {
        "nombre": NOMBRE_MODELO,
        "tipo": "lstm",
        "ventana": ventana,
        "horizonte": horizonte,
        "media": media,
        "desv": desv,
        "historia": [float(v) for v in serie],
        "state_dict": red.state_dict(),
        "semilla": semilla,
    }


def predecir(modelo, horizonte=None):
    """Pronóstico desnormalizado o None si no hay modelo válido."""
    if not isinstance(modelo, dict) or "state_dict" not in modelo:
        return None
    try:
        import torch

        ventana = int(modelo.get("ventana", VENTANA))
        horizonte_modelo = int(modelo.get("horizonte", HORIZONTE))
        horizonte = int(horizonte or horizonte_modelo)
        historia = [float(v) for v in modelo.get("historia", [])]
        # La red se entrenó con esa cabeza: no se puede pedir más de lo que
        # sabe predecir ni reconstruirla con otro horizonte (state_dict no encaja).
        if len(historia) < ventana or horizonte > horizonte_modelo:
            return None

        red = _construir_red(ventana, horizonte_modelo)
        red.load_state_dict(modelo["state_dict"])
        red.eval()

        x = torch.tensor(
            [[[v] for v in _normalizar(
                historia[-ventana:], modelo["media"], modelo["desv"]
            )]],
            dtype=torch.float32,
        )
        with torch.no_grad():
            y = red(x)[0].tolist()
        return _desnormalizar(y, modelo["media"], modelo["desv"])[:horizonte]
    except Exception:
        return None


def guardar_modelo(modelo, directorio=None):
    """Guarda en backend/ml_models/ (ignorado por Git)."""
    import torch

    destino = Path(directorio) if directorio else MODELOS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / ARCHIVO_MODELO
    torch.save(modelo, ruta)
    return ruta


def cargar_modelo(ruta):
    """Carga el .pt; None si no existe o falla."""
    import torch

    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    try:
        return torch.load(ruta, map_location="cpu", weights_only=True)
    except Exception:
        try:
            return torch.load(ruta, map_location="cpu", weights_only=False)
        except Exception:
            return None
