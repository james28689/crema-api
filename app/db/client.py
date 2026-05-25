import asyncpg
from asyncpg import Pool


async def create_pool(database_url: str) -> Pool:
    return await asyncpg.create_pool(dsn=database_url)


async def close_pool(pool: Pool) -> None:
    await pool.close()
