import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.models import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


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


async def get_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    """Email veya telefon numarası ile kullanıcı bulur."""
    result = await db.execute(
        select(User).where(
            or_(User.email == identifier, User.phone == identifier),
            User.deleted_at.is_(None),
        )
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
