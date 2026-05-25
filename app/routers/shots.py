from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user, get_db
from app.models.shots import BeanName, ShotCreate, ShotListResponse, ShotResponse

router = APIRouter(prefix="/v1/shots", tags=["shots"])

# ratio cast to float: asyncpg returns numeric / numeric as Decimal without the cast.
# days_off_roast_at_pull: DATE(pulled_at) gives the calendar date of the pull, minus
# beans.roast_date. Null when roast_date is null or bean has been deleted (LEFT JOIN).
_SHOT_COLS = """
    s.id,
    s.bean_id,
    s.dose_g,
    s.yield_g,
    (s.yield_g / s.dose_g)::float AS ratio,
    s.time_sec,
    s.grinder_setting,
    s.rating,
    s.taste_tags,
    s.notes,
    s.pulled_at,
    b.name AS bean_name,
    (DATE(s.pulled_at) - b.roast_date) AS days_off_roast_at_pull
"""


def _to_shot(row: asyncpg.Record) -> ShotResponse:
    data = dict(row)
    bean_name = data.pop("bean_name")
    bean_id = data.get("bean_id")
    data["bean"] = BeanName(id=bean_id, name=bean_name) if (bean_id and bean_name) else None
    return ShotResponse(**data)


@router.get("", response_model=ShotListResponse)
async def list_shots(
    bean_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: UUID | None = Query(default=None),
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> ShotListResponse:
    params: list = [user_id]
    clauses = ["s.user_id = $1"]

    if bean_id is not None:
        params.append(bean_id)
        clauses.append(f"s.bean_id = ${len(params)}")

    if cursor is not None:
        params.append(cursor)
        clauses.append(
            f"s.pulled_at < (SELECT pulled_at FROM shots WHERE id = ${len(params)})"
        )

    params.append(limit)

    rows = await conn.fetch(
        f"""
        SELECT {_SHOT_COLS}
        FROM shots s
        LEFT JOIN beans b ON b.id = s.bean_id
        WHERE {" AND ".join(clauses)}
        ORDER BY s.pulled_at DESC
        LIMIT ${len(params)}
        """,
        *params,
    )

    shots = [_to_shot(r) for r in rows]
    next_cursor = shots[-1].id if len(shots) == limit else None
    return ShotListResponse(data=shots, next_cursor=next_cursor)


@router.post("", response_model=ShotResponse, status_code=201)
async def create_shot(
    body: ShotCreate,
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> ShotResponse:
    bean_exists = await conn.fetchval(
        "SELECT id FROM beans WHERE id = $1 AND user_id = $2",
        body.bean_id,
        user_id,
    )
    if bean_exists is None:
        raise HTTPException(status_code=422, detail="bean_id not found or not owned by user")

    row = await conn.fetchrow(
        f"""
        WITH inserted AS (
            INSERT INTO shots
                (user_id, bean_id, dose_g, yield_g, time_sec, grinder_setting,
                 rating, taste_tags, notes, pulled_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, COALESCE($10, now()))
            RETURNING id
        )
        SELECT {_SHOT_COLS}
        FROM shots s
        LEFT JOIN beans b ON b.id = s.bean_id
        WHERE s.id = (SELECT id FROM inserted)
        """,
        user_id,
        body.bean_id,
        body.dose_g,
        body.yield_g,
        body.time_sec,
        body.grinder_setting,
        body.rating,
        body.taste_tags,
        body.notes,
        body.pulled_at,
    )
    return _to_shot(row)  # ty: ignore[invalid-argument-type]


@router.get("/{shot_id}", response_model=ShotResponse)
async def get_shot(
    shot_id: UUID,
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> ShotResponse:
    row = await conn.fetchrow(
        f"""
        SELECT {_SHOT_COLS}
        FROM shots s
        LEFT JOIN beans b ON b.id = s.bean_id
        WHERE s.id = $1 AND s.user_id = $2
        """,
        shot_id,
        user_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Shot not found")
    return _to_shot(row)


@router.delete("/{shot_id}", status_code=204)
async def delete_shot(
    shot_id: UUID,
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> None:
    deleted_id = await conn.fetchval(
        "DELETE FROM shots WHERE id = $1 AND user_id = $2 RETURNING id",
        shot_id,
        user_id,
    )
    if deleted_id is None:
        raise HTTPException(status_code=404, detail="Shot not found")
