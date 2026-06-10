from collections.abc import AsyncGenerator
from functools import lru_cache

import asyncpg
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException, Request

from app.config import get_settings


@lru_cache
def _get_jwks_client() -> PyJWKClient:
    return PyJWKClient(get_settings().SUPABASE_JWKS_URL)


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated",
        )
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    async with request.app.state.pool.acquire() as connection:
        yield connection
