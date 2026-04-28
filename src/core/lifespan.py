from contextlib import asynccontextmanager

import src.core.registry  # noqa: F401 — registers all models with Base.metadata
from src.core.database import Base, engine
from src.core.redis import close_redis, connect_redis


@asynccontextmanager
async def lifespan(_app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await connect_redis()
    try:
        yield
    finally:
        await close_redis()
        await engine.dispose()
