"""Async PostgreSQL connection pool for sentinel schema."""
from __future__ import annotations

import logging
import asyncpg
from app.config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        min_size=2,
        max_size=10,
    )
    logger.info(f"PostgreSQL pool created: {PG_HOST}:{PG_PORT}/{PG_DB}")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("PostgreSQL pool not initialized — call init_pool() first")
    return _pool
