from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user, get_db
from app.models.beans import BeanCreate, BeanResponse, BeanUpdate

router = APIRouter(prefix="/v1/beans", tags=["beans"])

# Reused column list for all bean SELECT queries.
# days_off_roast: PostgreSQL date - date returns int, null-safe when roast_date is null.
# shot_count: cast to int because COUNT returns bigint which Pydantic would accept but
# the explicit cast keeps the return type unambiguous.
_BEAN_COLS = """
    b.id,
    b.name,
    b.roaster,
    b.origin,
    b.process,
    b.roast_level,
    b.roast_date,
    b.is_active,
    b.created_at,
    (CURRENT_DATE - b.roast_date) AS days_off_roast,
    (SELECT COUNT(*) FROM shots s WHERE s.bean_id = b.id)::int AS shot_count
"""


def _to_bean(row: asyncpg.Record) -> BeanResponse:
    return BeanResponse(**dict(row))


async def _fetch_bean(
    conn: asyncpg.Connection,
    bean_id: UUID,
    user_id: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        f"SELECT {_BEAN_COLS} FROM beans b WHERE b.id = $1 AND b.user_id = $2",
        bean_id,
        user_id,
    )


@router.get("", response_model=list[BeanResponse])
async def list_beans(
    is_active: bool | None = Query(default=None),
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[BeanResponse]:
    params: list = [user_id]
    is_active_clause = ""
    if is_active is not None:
        is_active_clause = f"AND b.is_active = ${len(params) + 1}"
        params.append(is_active)

    rows = await conn.fetch(
        f"""
        SELECT {_BEAN_COLS}
        FROM beans b
        WHERE b.user_id = $1 {is_active_clause}
        ORDER BY b.created_at DESC
        """,
        *params,
    )
    return [_to_bean(r) for r in rows]


@router.post("", response_model=BeanResponse, status_code=201)
async def create_bean(
    body: BeanCreate,
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> BeanResponse:
    bean_id = await conn.fetchval(
        """
        INSERT INTO beans (user_id, name, roaster, origin, process, roast_level, roast_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """,
        user_id,
        body.name,
        body.roaster,
        body.origin,
        body.process,
        body.roast_level,
        body.roast_date,
    )
    row = await _fetch_bean(conn, bean_id, user_id)
    return _to_bean(row)  # ty: ignore[invalid-argument-type]


@router.get("/{bean_id}", response_model=BeanResponse)
async def get_bean(
    bean_id: UUID,
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> BeanResponse:
    row = await _fetch_bean(conn, bean_id, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bean not found")
    return _to_bean(row)


@router.patch("/{bean_id}", response_model=BeanResponse)
async def patch_bean(
    bean_id: UUID,
    body: BeanUpdate,
    user_id: str = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> BeanResponse:
    fields = body.model_fields_set
    if not fields:
        row = await _fetch_bean(conn, bean_id, user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Bean not found")
        return _to_bean(row)

    # Field names come from the Pydantic model definition, not user input — safe to
    # interpolate into SQL.
    assignments = ", ".join(f"{f} = ${i}" for i, f in enumerate(fields, start=1))
    values: list = [getattr(body, f) for f in fields]
    values.extend([user_id, bean_id])
    n = len(values)

    updated_id = await conn.fetchval(
        f"UPDATE beans SET {assignments} WHERE user_id = ${n - 1} AND id = ${n} RETURNING id",
        *values,
    )
    if updated_id is None:
        raise HTTPException(status_code=404, detail="Bean not found")

    row = await _fetch_bean(conn, bean_id, user_id)
    return _to_bean(row)  # ty: ignore[invalid-argument-type]
