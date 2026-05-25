"""
asyncpg connection pool setup.

create_pool(database_url: str) -> asyncpg.Pool
    Creates and returns an asyncpg connection pool. Called once at app startup
    and stored on app.state.pool.

close_pool(pool: asyncpg.Pool) -> None
    Gracefully closes all connections in the pool. Called at app shutdown.

The pool is consumed via the get_db() dependency in deps.py, which acquires a
connection per request and releases it on completion.
"""
