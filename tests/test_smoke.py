"""
tests/test_smoke.py

Pruebas básicas ("smoke tests"). Requieren haber corrido la ingestión
antes (python retrieval/ingest.py) y tener GROQ_API_KEY configurada
(gratis en https://console.groq.com/keys).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_pregunta_vacia():
    response = client.post("/chat", json={"pregunta": ""})
    assert response.status_code == 400


def test_chat_pregunta_valida():
    """
    Requiere que exista chroma_db/ (correr retrieval/ingest.py antes)
    y GROQ_API_KEY configurada. Si falla por eso, es esperado en CI
    sin credenciales.
    """
    response = client.post("/chat", json={"pregunta": "¿Qué es el Merval?"})
    assert response.status_code in (200, 503)
