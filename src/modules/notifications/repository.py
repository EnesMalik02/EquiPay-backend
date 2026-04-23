import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.notifications.models import Notification


async def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: str,
    data: dict | None = None,
) -> Notification:
    notification = Notification(user_id=user_id, type=type, data=data)
    db.add(notification)
    await db.flush()
    return notification


async def get_unread(db: AsyncSession, user_id: uuid.UUID) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalars().first()
    if not notification:
        return False
    notification.is_read = True
    await db.flush()
    return True
