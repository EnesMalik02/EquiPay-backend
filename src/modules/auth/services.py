import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.modules.users import repository as users_repo
from src.modules.users.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await users_repo.get_by_email(db, email)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    return await users_repo.get_by_username(db, username)


async def get_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    return await users_repo.get_by_identifier(db, identifier)


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await users_repo.get_by_id(db, user_id)


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
