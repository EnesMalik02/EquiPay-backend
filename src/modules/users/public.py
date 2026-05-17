import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users import services
from src.modules.users.models import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await services.get_by_id(db, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    return await services.get_by_email(db, email)


async def get_by_username(db: AsyncSession, username: str) -> User | None:
    return await services.get_by_username(db, username)


async def get_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    return await services.get_by_identifier(db, identifier)


async def create_user(db: AsyncSession, *, email: str, password: str, username: str) -> User:
    return await services.create_user(db, email=email, password=password, username=username)
