"""Gente, prueba mínima para ver que la API responde el health."""


def test_health(client):
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
