import os
import tempfile

# Antes de importar server.app (que arma la app al importarse), la base va a un
# directorio temporal para no tocar datos/ del repo.
os.environ.setdefault("TUTOR_DATOS", tempfile.mkdtemp(prefix="tutor-test-"))
os.environ.pop("CODIGOS_SECRETO", None)

import pytest
from fastapi.testclient import TestClient

from server import acceso, config
from server.app import crear_app

# El hash real usa 200 000 iteraciones; en los tests alcanza con menos.
acceso.ITERACIONES = 1_000

META_OK = (
    '<meta>{"ejercicio": "sep-01", "tipo_pedido": "orientacion", "escalon": 1, '
    '"error_detectado": null, "estado": "avanzando"}</meta>'
)


class TutorFalso:
    """Reemplaza la llamada a Claude: devuelve respuestas fijas y registra lo que recibió."""

    def __init__(self):
        self.respuestas: list[str] = []
        self.llamadas: list[tuple[str, list[dict]]] = []
        self.error: Exception | None = None

    def __call__(self, system, mensajes):
        self.llamadas.append((system, [dict(m) for m in mensajes]))
        if self.error:
            raise self.error
        texto = self.respuestas.pop(0) if self.respuestas else "¿Qué tipo de ecuación es? " + META_OK
        return texto, "modelo-de-prueba"


@pytest.fixture
def ajustes(tmp_path):
    return config.Ajustes(datos=tmp_path / "datos", system_prompt=tmp_path / "no-existe.md", codigos_secreto=None)


@pytest.fixture
def tutor():
    return TutorFalso()


@pytest.fixture
def app(ajustes, tutor):
    app = crear_app(ajustes, responder=tutor)
    app.state.bd.guardar_estudiante("EST-07", acceso.hash_codigo("ABC234"))
    app.state.bd.guardar_estudiante("EST-08", acceso.hash_codigo("XYZ789"))
    return app


@pytest.fixture
def cliente(app):
    return TestClient(app)


@pytest.fixture
def token(cliente):
    r = cliente.post("/api/login", json={"id": "EST-07", "codigo": "ABC234"})
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}
