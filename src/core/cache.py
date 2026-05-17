from redis.asyncio import Redis

from src.core.redis import redis_client


class CacheKeys:
    @staticmethod
    def expense_detail(expense_id: str) -> str:
        return f"expense:{expense_id}:detail"

    @staticmethod
    def group_detail(group_id: str, user_id: str) -> str:
        return f"group:{group_id}:detail:user:{user_id}"

    @staticmethod
    def group_detail_pattern(group_id: str) -> str:
        return f"group:{group_id}:detail:*"

    @staticmethod
    def group_stats(group_id: str) -> str:
        return f"group:{group_id}:stats"


class CacheTTL:
    EXPENSE_DETAIL: int = 300
    GROUP_DETAIL: int = 300
    GROUP_STATS: int = 600


class CacheService:
    @property
    def _r(self) -> Redis:
        return redis_client

    async def get_str(self, key: str) -> str | None:
        return await self._r.get(key)

    async def set_str(self, key: str, value: str, ttl: int) -> None:
        await self._r.setex(key, ttl, value)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        cursor = 0
        while True:
            cursor, keys = await self._r.scan(cursor, match=pattern, count=100)
            if keys:
                await self._r.delete(*keys)
            if cursor == 0:
                break

    async def invalidate_group_detail(self, group_id: str) -> None:
        await self.delete_pattern(CacheKeys.group_detail_pattern(group_id))

    async def invalidate_group_stats(self, group_id: str) -> None:
        await self.delete(CacheKeys.group_stats(group_id))

    async def invalidate_expense_detail(self, expense_id: str) -> None:
        await self.delete(CacheKeys.expense_detail(expense_id))


cache = CacheService()
