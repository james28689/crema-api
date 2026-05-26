import uuid
from datetime import datetime, timezone

import pytest

BEAN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SHOT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PULLED_AT = datetime(2026, 4, 27, 8, 31, 0, tzinfo=timezone.utc)

DOSE_G = 18.0
YIELD_G = 41.0


def _shot_row(**kwargs):
    return {
        "id": SHOT_ID,
        "bean_id": BEAN_ID,
        "dose_g": DOSE_G,
        "yield_g": YIELD_G,
        "ratio": YIELD_G / DOSE_G,
        "time_sec": 28,
        "grinder_setting": "3.5",
        "rating": 8,
        "taste_tags": ["balanced", "bright"],
        "notes": "Clean finish",
        "pulled_at": PULLED_AT,
        "days_off_roast_at_pull": 17,
        "bean_name": "Ethiopia Yirgacheffe",
        **kwargs,
    }


_SHOT_BODY = {
    "bean_id": str(BEAN_ID),
    "dose_g": DOSE_G,
    "yield_g": YIELD_G,
    "time_sec": 28,
}


def test_create_shot_happy_path(client, mock_conn):
    mock_conn.fetchval.return_value = BEAN_ID  # bean ownership check
    mock_conn.fetchrow.return_value = _shot_row()

    resp = client.post("/v1/shots", json=_SHOT_BODY)

    assert resp.status_code == 201
    body = resp.json()
    # Done-state assertion from crema-api.md
    assert body["ratio"] == pytest.approx(YIELD_G / DOSE_G)
    assert body["bean"]["name"] == "Ethiopia Yirgacheffe"
    assert "id" in body


def test_create_shot_bean_not_owned(client, mock_conn):
    mock_conn.fetchval.return_value = None  # bean ownership check fails

    resp = client.post("/v1/shots", json=_SHOT_BODY)

    assert resp.status_code == 403
    assert "error" in resp.json()


def test_list_shots_cursor_pagination(client, mock_conn):
    shot_a_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    shot_b_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    mock_conn.fetch.return_value = [
        _shot_row(id=shot_a_id),
        _shot_row(id=shot_b_id),
    ]

    resp = client.get("/v1/shots?limit=2")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    # next_cursor is the id of the last item when len(results) == limit
    assert body["next_cursor"] == str(shot_b_id)


def test_list_shots_no_next_cursor_on_last_page(client, mock_conn):
    mock_conn.fetch.return_value = [_shot_row()]  # 1 result, limit defaults to 20

    resp = client.get("/v1/shots")

    assert resp.status_code == 200
    assert resp.json()["next_cursor"] is None


def test_delete_shot_success(client, mock_conn):
    mock_conn.fetchval.return_value = SHOT_ID

    resp = client.delete(f"/v1/shots/{SHOT_ID}")

    assert resp.status_code == 204


def test_delete_shot_not_found(client, mock_conn):
    mock_conn.fetchval.return_value = None

    resp = client.delete(f"/v1/shots/{SHOT_ID}")

    assert resp.status_code == 404
    assert "error" in resp.json()


def test_get_shot(client, mock_conn):
    mock_conn.fetchrow.return_value = _shot_row()

    resp = client.get(f"/v1/shots/{SHOT_ID}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(SHOT_ID)


def test_get_shot_not_found(client, mock_conn):
    mock_conn.fetchrow.return_value = None

    resp = client.get(f"/v1/shots/{SHOT_ID}")

    assert resp.status_code == 404


@pytest.mark.parametrize("body,expected_loc", [
    ({**_SHOT_BODY, "dose_g": -1}, "dose_g"),
    ({**_SHOT_BODY, "yield_g": 0}, "yield_g"),
    ({**_SHOT_BODY, "rating": 11}, "rating"),
    ({k: v for k, v in _SHOT_BODY.items() if k != "time_sec"}, "time_sec"),
])
def test_create_shot_validation(client, body, expected_loc):
    resp = client.post("/v1/shots", json=body)

    assert resp.status_code == 422
    assert expected_loc in resp.json()["error"]["message"]
