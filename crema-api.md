# Crema — API Plan
> Increment 1 reference document. Last updated: 2026-04-28

---

## Stack

- **Runtime:** Python FastAPI
- **Base path:** `/v1/`
- **Auth:** JWT bearer token issued by Supabase Auth after Google Sign-in. The FastAPI backend verifies the JWT using the Supabase JWT secret — it does not issue its own tokens.
- **Validation:** Pydantic
- **DB client:** `asyncpg` or `supabase-py`

---

## Auth flow

Authentication is handled entirely by Supabase Auth on the client. The FastAPI backend only verifies the resulting JWT — it never exchanges OAuth tokens or creates users.

```
Mobile app
  → Google Sign-In (OAuth via Supabase Auth SDK)
  → Supabase verifies Google ID token with Google JWKS
  → Supabase creates / upserts auth.users row
  → Supabase returns access_token (JWT) + refresh_token to client
  → Client stores JWT, sends as Authorization: Bearer <token> on every API request
  → FastAPI verifies JWT signature using Supabase JWT secret
  → Extracts sub claim (= auth.users UUID) as user_id for all queries
```

There is **no** `POST /v1/auth/signin` route. Sign-in is a client-side operation using the Supabase Auth SDK.

### FastAPI JWT verification

```python
import jwt
from fastapi import Depends, HTTPException, Header

SUPABASE_JWT_SECRET = "your-jwt-secret"  # Supabase project Settings → API

async def get_current_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401)
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload["sub"]  # auth.users UUID — use as user_id in all queries
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

---

## Middleware stack (every request)

```
Request
  → JWT verify (reject 401 if missing or invalid)
  → Rate limit (100 req/min per user)
  → Pydantic body validation (reject 422 if invalid)
  → Route handler
  → Error handler (standardised error envelope)
Response
```

### Standard error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "dose_g is required",
    "status": 422
  }
}
```

---

## Routes — Increment 1

> There are no auth routes. See Auth flow above.

### Beans

#### `GET /v1/beans`
List all beans for the authed user.

**Auth:** JWT required

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `is_active` | boolean | (none) | Filter active or archived bags |

**Response 200:**
```json
[
  {
    "id": "uuid",
    "name": "Ethiopia Yirgacheffe",
    "roaster": "Square Mile",
    "origin": "Ethiopia",
    "process": "washed",
    "roast_level": "light",
    "roast_date": "2026-04-10",
    "days_off_roast": 17,
    "is_active": true,
    "shot_count": 8,
    "created_at": "2026-04-10T10:00:00Z"
  }
]
```

**Notes:**
- `days_off_roast` = `CURRENT_DATE - roast_date`, computed in SQL, null if `roast_date` is null
- `shot_count` = COUNT of shots with this `bean_id`, computed via JOIN / subquery
- Ordered by `created_at DESC`

---

#### `POST /v1/beans`
Add a new bean / bag.

**Auth:** JWT required

**Request body:**
```json
{
  "name": "Ethiopia Yirgacheffe",
  "roaster": "Square Mile",
  "origin": "Ethiopia",
  "process": "washed",
  "roast_level": "light",
  "roast_date": "2026-04-10"
}
```

**Validation:**
- `name` — required, non-empty string
- `process` — optional, must be one of `washed | natural | honey`
- `roast_level` — optional, must be one of `light | medium | dark`
- `roast_date` — optional, ISO date string `YYYY-MM-DD`

**Response 201:** Full bean object (same shape as GET list item)

---

#### `GET /v1/beans/:id`
Get a single bean with shot summary.

**Auth:** JWT required

**Response 200:** Full bean object. 404 if not found or not owned by user.

---

#### `PATCH /v1/beans/:id`
Partial update — archive a bag, correct a field.

**Auth:** JWT required

**Request body (any subset):**
```json
{
  "is_active": false,
  "roast_date": "2026-04-12"
}
```

**Response 200:** Updated bean object.

---

### Shots

#### `GET /v1/shots`
Paginated shot history.

**Auth:** JWT required

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `bean_id` | uuid | (none) | Filter by bean |
| `limit` | integer | 20 | Page size, max 100 |
| `cursor` | uuid | (none) | ID of last item from previous page |

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "bean_id": "uuid",
      "bean": { "name": "Ethiopia Yirgacheffe" },
      "dose_g": 18.0,
      "yield_g": 41.0,
      "ratio": 2.28,
      "time_sec": 28,
      "grinder_setting": "3.5",
      "rating": 8,
      "taste_tags": ["balanced", "bright"],
      "notes": "Slightly long but clean finish",
      "pulled_at": "2026-04-27T08:31:00Z",
      "days_off_roast_at_pull": 17
    }
  ],
  "next_cursor": "uuid" | null
}
```

**Notes:**
- `ratio` = `yield_g / dose_g` computed in SQL
- `days_off_roast_at_pull` = `DATE(pulled_at) - beans.roast_date` — the age of the bean *when the shot was pulled*, not today
- Cursor pagination: `WHERE pulled_at < (SELECT pulled_at FROM shots WHERE id = $cursor) ORDER BY pulled_at DESC`
- Joined bean name comes from a LEFT JOIN (null-safe — bean may have been deleted)

---

#### `POST /v1/shots`
Log a new shot.

**Auth:** JWT required

**Request body:**
```json
{
  "bean_id": "uuid",
  "dose_g": 18.0,
  "yield_g": 41.0,
  "time_sec": 28,
  "grinder_setting": "3.5",
  "rating": 8,
  "taste_tags": ["balanced"],
  "notes": "Slightly long but clean finish",
  "pulled_at": "2026-04-27T08:31:00Z"
}
```

**Validation:**
- `bean_id` — required, must exist and belong to the authed user
- `dose_g`, `yield_g` — required, positive numbers
- `time_sec` — required, positive integer
- `rating` — optional, integer 1–10
- `taste_tags` — optional array of strings
- `pulled_at` — optional ISO timestamp, defaults to `now()`

**Response 201:** Full shot object (same shape as GET list item)

---

#### `GET /v1/shots/:id`
Get a single shot with full detail.

**Auth:** JWT required

**Response 200:** Full shot object including joined bean name and `days_off_roast_at_pull`. 404 if not found or not owned by user.

---

#### `DELETE /v1/shots/:id`
Delete a logged shot.

**Auth:** JWT required

**Response 204:** No content.

**Note:** Hard delete in Increment 1. No soft delete.

---

## HTTP status codes used

| Code | Meaning |
|---|---|
| 200 | OK |
| 201 | Created |
| 204 | No content (delete) |
| 400 | Bad request (malformed JSON, etc.) |
| 401 | Unauthorised (missing or invalid JWT) |
| 403 | Forbidden (resource exists but not owned by user) |
| 404 | Not found |
| 422 | Unprocessable entity (validation failure) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Computed values summary

| Field | Formula | Returned on |
|---|---|---|
| `ratio` | `yield_g / dose_g` | GET /shots, POST /shots response |
| `days_off_roast` | `CURRENT_DATE - beans.roast_date` | GET /beans (today's value) |
| `days_off_roast_at_pull` | `DATE(pulled_at) - beans.roast_date` | GET /shots (historical value) |
| `shot_count` | `COUNT(shots.bean_id)` | GET /beans |

---

## Routes not in Increment 1

These are deferred to later increments:

| Route | Increment | Purpose |
|---|---|---|
| `GET /v1/insights/timeline` | 3 | Shot number vs. rating per bag |
| `GET /v1/insights/correlations` | 4 | Pearson coefficient per variable vs. rating |
| `GET /v1/recommendations` | 5 | Dial-in wizard — similarity match + suggested params |

---

## Done state for Increment 1

`POST /v1/shots` returns 201 with a full shot object including `ratio`, a joined `bean.name`, and the correct `user_id` (extracted from the Supabase JWT). This confirms JWT verification, Pydantic validation, FK integrity, and computed field logic all work end-to-end.