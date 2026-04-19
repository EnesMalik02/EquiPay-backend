import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.modules.users import repository
from src.modules.users.models import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    return await repository.get_by_email(db, email)


async def get_by_phone(db: AsyncSession, phone: str) -> User | None:
    return await repository.get_by_phone(db, phone)


async def search_by_email(
    db: AsyncSession, email: str, *, exclude_id: uuid.UUID, limit: int = 10
) -> list[User]:
    return await repository.search_by_email(db, email, exclude_id=exclude_id, limit=limit)


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
