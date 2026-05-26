import uuid
from datetime import date, datetime, timezone

BEAN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CREATED_AT = datetime(2026, 4, 10, 10, 0, 0, tzinfo=timezone.utc)


def _bean_row(**kwargs):
    return {
        "id": BEAN_ID,
        "name": "Ethiopia Yirgacheffe",
        "roaster": "Square Mile",
        "origin": "Ethiopia",
        "process": "washed",
        "roast_level": "light",
        "roast_date": date(2026, 4, 10),
        "is_active": True,
        "created_at": CREATED_AT,
        "days_off_roast": 17,
        "shot_count": 3,
        **kwargs,
    }


def test_create_bean_happy_path(client, mock_conn):
    mock_conn.fetchrow.return_value = _bean_row()

    resp = client.post("/v1/beans", json={"name": "Ethiopia Yirgacheffe", "process": "washed"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Ethiopia Yirgacheffe"
    assert body["process"] == "washed"
    assert body["shot_count"] == 3
    assert body["days_off_roast"] == 17


def test_create_bean_missing_name(client, mock_conn):
    resp = client.post("/v1/beans", json={"roaster": "Square Mile"})

    assert resp.status_code == 422
    assert "error" in resp.json()


def test_create_bean_invalid_process(client, mock_conn):
    resp = client.post("/v1/beans", json={"name": "Test Bean", "process": "unknown"})

    assert resp.status_code == 422
    assert "error" in resp.json()


def test_list_beans_returns_user_scoped_list(client, mock_conn):
    rows = [_bean_row(), _bean_row(id=uuid.uuid4(), name="Kenya Kirinyaga")]
    mock_conn.fetch.return_value = rows

    resp = client.get("/v1/beans")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["name"] == "Ethiopia Yirgacheffe"
    assert body[1]["name"] == "Kenya Kirinyaga"
    # user_id must not leak into the response
    assert "user_id" not in body[0]


def test_list_beans_is_active_filter(client, mock_conn):
    mock_conn.fetch.return_value = []

    client.get("/v1/beans?is_active=false")

    call_args = mock_conn.fetch.call_args
    assert "is_active" in call_args.args[0]


def test_get_bean(client, mock_conn):
    mock_conn.fetchrow.return_value = _bean_row()

    resp = client.get(f"/v1/beans/{BEAN_ID}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(BEAN_ID)


def test_get_bean_not_found(client, mock_conn):
    mock_conn.fetchrow.return_value = None

    resp = client.get(f"/v1/beans/{BEAN_ID}")

    assert resp.status_code == 404
    assert resp.json() == {"error": {"message": "Bean not found", "status": 404}}


def test_patch_bean(client, mock_conn):
    mock_conn.fetchval.return_value = BEAN_ID
    mock_conn.fetchrow.return_value = _bean_row(is_active=False)

    resp = client.patch(f"/v1/beans/{BEAN_ID}", json={"is_active": False})

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_patch_bean_not_found(client, mock_conn):
    mock_conn.fetchval.return_value = None

    resp = client.patch(f"/v1/beans/{BEAN_ID}", json={"is_active": False})

    assert resp.status_code == 404
