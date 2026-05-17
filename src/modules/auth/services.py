import uuid

import jwt
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.security import verify_password
from src.modules.users import public as users_public
from src.modules.users.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await users_public.get_by_email(db, email)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    return await users_public.get_by_username(db, username)


async def get_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    return await users_public.get_by_identifier(db, identifier)


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await users_public.get_by_id(db, user_id)


async def register(db: AsyncSession, *, email: str, password: str, username: str) -> uuid.UUID:
    if await users_public.get_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu email adresi zaten kayıtlı.")
    if await users_public.get_by_username(db, username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu kullanıcı adı zaten alınmış.")
    try:
        user = await users_public.create_user(db, email=email, password=password, username=username)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kayıt sırasında bir çakışma oluştu.")
    return user.id


async def authenticate(db: AsyncSession, identifier: str, password: str) -> uuid.UUID:
    user = await users_public.get_by_identifier(db, identifier)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email/username or password is incorrect.")
    return user.id


async def validate_refresh_token(db: AsyncSession, token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz refresh token türü veya içeriği.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token süresi dolmuş. Lütfen tekrar giriş yapın.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz refresh token.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kullanıcı kimliği.")

    user = await users_public.get_by_id(db, user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı.")
    return user.id
