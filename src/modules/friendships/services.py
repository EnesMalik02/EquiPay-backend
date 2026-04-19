import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.friendships import repository
from src.modules.friendships.models import Friendship
from src.modules.users import services as users_services


async def send_request(
    db: AsyncSession,
    *,
    requester_id: uuid.UUID,
    addressee_email: str | None = None,
    addressee_phone: str | None = None,
) -> Friendship:
    if addressee_phone:
        addressee = await users_services.get_by_phone(db, addressee_phone)
        if not addressee:
            raise LookupError("Bu telefon numarasına kayıtlı kullanıcı bulunamadı.")
    else:
        addressee = await users_services.get_by_email(db, addressee_email)
        if not addressee:
            raise LookupError("Bu email'e kayıtlı kullanıcı bulunamadı.")

    if addressee.id == requester_id:
        raise ValueError("Kendinize arkadaşlık isteği gönderemezsiniz.")

    existing = await repository.get_existing(db, requester_id, addressee.id)
    if existing:
        raise ValueError("Bu kullanıcı ile zaten bir arkadaşlık kaydı var.")

    friendship = Friendship(requester_id=requester_id, addressee_id=addressee.id)
    db.add(friendship)
    await db.flush()
    await db.refresh(friendship)
    return friendship


async def get_friends(db: AsyncSession, user_id: uuid.UUID) -> list[Friendship]:
    return await repository.get_friends(db, user_id)


async def get_pending_requests(db: AsyncSession, user_id: uuid.UUID) -> list[Friendship]:
    return await repository.get_pending_requests(db, user_id)


async def get_friendship_by_id(
    db: AsyncSession, friendship_id: uuid.UUID
) -> Friendship | None:
    return await repository.get_by_id(db, friendship_id)


async def accept_request(db: AsyncSession, friendship: Friendship) -> Friendship:
    friendship.status = "accepted"
    await db.flush()
    await db.refresh(friendship)
    return friendship


async def delete_friendship(db: AsyncSession, friendship: Friendship) -> None:
    await db.delete(friendship)
    await db.flush()
