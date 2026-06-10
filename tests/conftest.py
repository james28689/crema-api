import os

# Must be set before any app import triggers get_settings().
os.environ.setdefault("SUPABASE_JWKS_URL", "https://example.supabase.co/.well-known/jwks.json")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetch.return_value = []
    conn.fetchrow.return_value = None
    conn.fetchval.return_value = None
    return conn


@pytest.fixture
def client(mock_conn):
    def override_get_current_user() -> str:
        return TEST_USER_ID

    async def override_get_db():
        yield mock_conn

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.main.create_pool", new_callable=AsyncMock) as mock_create,
        patch("app.main.close_pool", new_callable=AsyncMock),
    ):
        mock_create.return_value = MagicMock()
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
