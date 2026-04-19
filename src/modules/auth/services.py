import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.models import User
from src.core.security import hash_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    """Email veya kullanıcı adı ile kullanıcı bulur."""
    result = await db.execute(
        select(User).where(
            or_(User.email == identifier, User.username == identifier),
            User.deleted_at.is_(None),
        )
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    phone: str,
    username: str,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        username=username,
        phone=phone,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
