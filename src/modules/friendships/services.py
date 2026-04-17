import uuid

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.friendships.models import Friendship
from src.modules.users import services as user_services
from src.modules.users.models import User


async def send_request(
    db: AsyncSession,
    *,
    requester_id: uuid.UUID,
    addressee_email: str | None = None,
    addressee_phone: str | None = None,
) -> Friendship:
    if addressee_phone:
        addressee = await user_services.get_by_phone(db, addressee_phone)
        if not addressee:
            raise LookupError("Bu telefon numarasına kayıtlı kullanıcı bulunamadı.")
    else:
        addressee = await user_services.get_by_email(db, addressee_email)
        if not addressee:
            raise LookupError("Bu email'e kayıtlı kullanıcı bulunamadı.")

    if addressee.id == requester_id:
        raise ValueError("Kendinize arkadaşlık isteği gönderemezsiniz.")

    existing = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == requester_id, Friendship.addressee_id == addressee.id),
                and_(Friendship.requester_id == addressee.id, Friendship.addressee_id == requester_id),
            )
        )
    )
    if existing.scalars().first():
        raise ValueError("Bu kullanıcı ile zaten bir arkadaşlık kaydı var.")

    friendship = Friendship(requester_id=requester_id, addressee_id=addressee.id)
    db.add(friendship)
    await db.flush()
    await db.refresh(friendship)
    return friendship


async def get_friends(db: AsyncSession, user_id: uuid.UUID) -> list[Friendship]:
    result = await db.execute(
        select(Friendship)
        .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
        .where(
            Friendship.status == "accepted",
            or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
        )
    )
    return list(result.scalars().all())


async def get_pending_requests(db: AsyncSession, user_id: uuid.UUID) -> list[Friendship]:
    result = await db.execute(
        select(Friendship)
        .options(selectinload(Friendship.requester))
        .where(Friendship.addressee_id == user_id, Friendship.status == "pending")
        .order_by(Friendship.created_at.desc())
    )
    return list(result.scalars().all())


async def get_friendship_by_id(db: AsyncSession, friendship_id: uuid.UUID) -> Friendship | None:
    result = await db.execute(
        select(Friendship)
        .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
        .where(Friendship.id == friendship_id)
    )
    return result.scalars().first()


async def accept_request(db: AsyncSession, friendship: Friendship) -> Friendship:
    friendship.status = "accepted"
    await db.flush()
    await db.refresh(friendship)
    return friendship


async def delete_friendship(db: AsyncSession, friendship: Friendship) -> None:
    await db.delete(friendship)
    await db.flush()
