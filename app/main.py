import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.client import close_pool, create_pool
from app.deps import _get_jwks_client
from app.routers import beans, shots

_RATE_LIMIT = 100
_WINDOW_SEC = 60

# user_id → timestamps of recent requests within the current window
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"message": message, "status": status}},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.pool = await create_pool(settings.DATABASE_URL)
    yield
    await close_pool(app.state.pool)


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return await call_next(request)

    token = authorization.removeprefix("Bearer ")
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
        )
        user_id: str = payload["sub"]
    except jwt.PyJWTError:
        return await call_next(request)

    now = time.monotonic()
    bucket = _rate_buckets[user_id]
    while bucket and bucket[0] <= now - _WINDOW_SEC:
        bucket.popleft()

    if len(bucket) >= _RATE_LIMIT:
        return _error("Rate limit exceeded: 100 requests per minute", 429)

    bucket.append(now)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    msg = first.get("msg", "Validation error")
    return _error(f"{loc}: {msg}" if loc else msg, 422)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _error(str(exc.detail), exc.status_code)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error("An unexpected error occurred", 500)


app.include_router(beans.router)
app.include_router(shots.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
