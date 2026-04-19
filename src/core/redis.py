from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from src.config import settings

# ──────────────────────────────────────────────
# Connection Pool
# ──────────────────────────────────────────────
_pool: ConnectionPool = ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)

redis_client: Redis = Redis(connection_pool=_pool)


# ──────────────────────────────────────────────
# Lifecycle
# ──────────────────────────────────────────────
async def connect_redis() -> None:
    await redis_client.ping()


async def close_redis() -> None:
    await redis_client.aclose()
    await _pool.aclose()


# ──────────────────────────────────────────────
# FastAPI Dependency
# ──────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[Redis, None]:
    yield redis_client
