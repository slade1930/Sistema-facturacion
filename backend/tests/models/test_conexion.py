import os

import pytest
from sqlalchemy import text

from app.db.session import URL_POR_DEFECTO, get_engine


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Sin DATABASE_URL")
def test_conexion_postgres():
    with get_engine().connect() as conexion:
        assert conexion.execute(text("SELECT 1")).scalar_one() == 1


def test_url_por_defecto_esta_definida():
    assert URL_POR_DEFECTO.startswith("postgresql+psycopg://")