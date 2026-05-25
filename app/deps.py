"""
FastAPI dependencies shared across routers.

get_current_user(authorization: str = Header(...)) -> str
    Verifies the Bearer JWT from the Authorization header using the Supabase JWT
    secret (HS256, audience="authenticated"). Returns the `sub` claim, which is
    the auth.users UUID used as user_id in all database queries.
    Raises HTTP 401 on missing, malformed, or expired tokens.

get_db() -> asyncpg.Connection
    Yields a connection from the shared asyncpg pool (acquired from app state).
    Releases the connection back to the pool after the request completes.
"""
