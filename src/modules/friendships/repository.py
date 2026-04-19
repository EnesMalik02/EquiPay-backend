import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.friendships.models import Friendship


async def get_friends(db: AsyncSession, user_id: uuid.UUID) -> list[Friendship]:
    result = await db.execute(
        select(Friendship)
        .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
        .where(
            Friendship.status == "accepted",
            or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
        )
    )
    return list(result.scalars().all())


async def get_pending_requests(db: AsyncSession, user_id: uuid.UUID) -> list[Friendship]:
    result = await db.execute(
        select(Friendship)
        .options(selectinload(Friendship.requester))
        .where(Friendship.addressee_id == user_id, Friendship.status == "pending")
        .order_by(Friendship.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, friendship_id: uuid.UUID) -> Friendship | None:
    result = await db.execute(
        select(Friendship)
        .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
        .where(Friendship.id == friendship_id)
    )
    return result.scalars().first()


async def get_existing(
    db: AsyncSession, user1_id: uuid.UUID, user2_id: uuid.UUID
) -> Friendship | None:
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(
                    Friendship.requester_id == user1_id,
                    Friendship.addressee_id == user2_id,
                ),
                and_(
                    Friendship.requester_id == user2_id,
                    Friendship.addressee_id == user1_id,
                ),
            )
        )
    )
    return result.scalars().first()
