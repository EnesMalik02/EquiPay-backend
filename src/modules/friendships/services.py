import uuid
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.friendships.models import Friendship
from src.modules.users.models import User


async def send_request(
    db: AsyncSession,
    *,
    requester_id: uuid.UUID,
    addressee_email: str | None = None,
    addressee_phone: str | None = None,
) -> Friendship:
    from fastapi import HTTPException, status

    if addressee_phone:
        result = await db.execute(
            select(User).where(User.phone == addressee_phone, User.deleted_at.is_(None))
        )
        label = "Bu telefon numarasına"
    else:
        result = await db.execute(
            select(User).where(User.email == addressee_email, User.deleted_at.is_(None))
        )
        label = "Bu email'e"

    addressee = result.scalars().first()
    if not addressee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} kayıtlı kullanıcı bulunamadı.")

    if addressee.id == requester_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendinize arkadaşlık isteği gönderemezsiniz.")

    existing = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == requester_id, Friendship.addressee_id == addressee.id),
                and_(Friendship.requester_id == addressee.id, Friendship.addressee_id == requester_id),
            )
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu kullanıcı ile zaten bir arkadaşlık kaydı var.")

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
