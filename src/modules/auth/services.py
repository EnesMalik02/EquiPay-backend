import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.models import User
from src.core.security import hash_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def generate_unique_username(db: AsyncSession, base: str) -> str:
    candidate = base[:50]
    result = await db.execute(select(User).where(User.username == candidate))
    if not result.scalars().first():
        return candidate
    suffix = str(uuid.uuid4())[:8]
    return f"{candidate[:40]}_{suffix}"


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    phone: str,
    display_name: str | None = None,
    username: str | None = None,
) -> User:
    if not username:
        base = email.split("@")[0]
        username = await generate_unique_username(db, base)

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        username=username,
        phone=phone,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
