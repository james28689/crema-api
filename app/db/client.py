import asyncpg
from asyncpg import Pool


async def create_pool(database_url: str, max_size: int = 10) -> Pool:
    return await asyncpg.create_pool(dsn=database_url, min_size=1, max_size=max_size)


async def close_pool(pool: Pool) -> None:
    await pool.close()
