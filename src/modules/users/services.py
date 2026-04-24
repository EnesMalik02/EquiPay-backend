import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.modules.users import repository
from src.modules.users.models import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await repository.get_by_id(db, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    return await repository.get_by_email(db, email)


async def get_by_phone(db: AsyncSession, phone: str) -> User | None:
    return await repository.get_by_phone(db, phone)


async def get_by_username(db: AsyncSession, username: str) -> User | None:
    return await repository.get_by_username(db, username)


async def search_by_email(
    db: AsyncSession, email: str, *, exclude_id: uuid.UUID, limit: int = 10
) -> list[User]:
    return await repository.search_by_email(db, email, exclude_id=exclude_id, limit=limit)


async def update_profile(
    db: AsyncSession,
    user: User,
    *,
    email: str | None = None,
    display_name: str | None = None,
    username: str | None = None,
    phone: str | None = None,
) -> User:
    from fastapi import HTTPException, status
    if email and email != user.email:
        existing = await repository.get_by_email(db, email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kullanılıyor.")
    if username and username != user.username:
        existing = await repository.get_by_username(db, username)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu kullanıcı adı zaten kullanılıyor.")
    if phone and phone != user.phone:
        existing = await repository.get_by_phone(db, phone)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu telefon numarası zaten kullanılıyor.")
    return await repository.update_profile(
        db, user, email=email, display_name=display_name, username=username, phone=phone
    )


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
