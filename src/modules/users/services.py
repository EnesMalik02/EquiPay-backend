import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.models import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(
        select(User).where(User.phone == phone, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def search_by_email(
    db: AsyncSession, email: str, *, exclude_id: uuid.UUID, limit: int = 10
) -> list[User]:
    result = await db.execute(
        select(User)
        .where(
            User.email.ilike(f"%{email}%"),
            User.id != exclude_id,
            User.deleted_at.is_(None),
        )
        .limit(limit)
    )
    return list(result.scalars().all())
