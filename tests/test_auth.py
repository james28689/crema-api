"""Auth middleware and error envelope shape tests."""
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


@contextmanager
def _plain_client():
    """Client with no dependency overrides — exercises real auth middleware."""
    with (
        patch("app.main.create_pool", new_callable=AsyncMock) as mock_create,
        patch("app.main.close_pool", new_callable=AsyncMock),
    ):
        mock_create.return_value = MagicMock()
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_missing_auth_header_returns_401():
    with _plain_client() as client:
        resp = client.get("/v1/beans")
    assert resp.status_code == 401


def test_invalid_token_returns_401():
    with _plain_client() as client:
        resp = client.get("/v1/beans", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_health_requires_no_auth():
    with _plain_client() as client:
        resp = client.get("/health")
    assert resp.status_code == 200


def test_error_envelope_shape():
    with _plain_client() as client:
        resp = client.get("/v1/beans")
    assert resp.json() == {"error": {"message": "Invalid authorization header", "status": 401}}
