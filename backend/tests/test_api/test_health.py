"""
Smoke test: verify the FastAPI app starts and /health returns 200.

Person 1 owns this file. Add more integration tests here as routes are implemented.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
