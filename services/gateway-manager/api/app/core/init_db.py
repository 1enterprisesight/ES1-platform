"""Database initialization utilities."""
from sqlalchemy.ext.asyncio import AsyncEngine
from app.core.database import Base, engine


async def create_tables(engine_instance: AsyncEngine = None):
    """Create all database tables if they don't exist."""
    if engine_instance is None:
        engine_instance = engine

    async with engine_instance.begin() as conn:
        # Create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(engine_instance: AsyncEngine = None):
    """Drop all database tables. USE WITH CAUTION!"""
    if engine_instance is None:
        engine_instance = engine

    async with engine_instance.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
