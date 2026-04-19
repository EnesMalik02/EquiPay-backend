import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.settlements.models import Settlement


async def get_by_id(db: AsyncSession, settlement_id: uuid.UUID) -> Settlement | None:
    result = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    )
    return result.scalars().first()


async def get_by_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(Settlement.group_id == group_id)
        .order_by(Settlement.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(
            (Settlement.payer_id == user_id) | (Settlement.receiver_id == user_id)
        )
        .order_by(Settlement.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
