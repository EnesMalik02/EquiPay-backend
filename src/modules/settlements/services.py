import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.settlements.models import Settlement


async def create_settlement(
    db: AsyncSession,
    *,
    group_id: uuid.UUID | None,
    payer_id: uuid.UUID,
    receiver_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    note: str | None = None,
) -> Settlement:
    settlement = Settlement(
        group_id=group_id,
        payer_id=payer_id,
        receiver_id=receiver_id,
        amount=amount,
        currency=currency,
        note=note,
    )
    db.add(settlement)
    await db.flush()
    await db.refresh(settlement)
    return settlement


async def get_settlement_by_id(
    db: AsyncSession, settlement_id: uuid.UUID
) -> Settlement | None:
    result = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    )
    return result.scalars().first()


async def get_group_settlements(
    db: AsyncSession, group_id: uuid.UUID
) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(Settlement.group_id == group_id)
        .order_by(Settlement.created_at.desc())
    )
    return list(result.scalars().all())


async def get_user_settlements(
    db: AsyncSession, user_id: uuid.UUID
) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(
            (Settlement.payer_id == user_id) | (Settlement.receiver_id == user_id)
        )
        .order_by(Settlement.created_at.desc())
    )
    return list(result.scalars().all())


_VALID_STATUSES = frozenset({"confirmed", "rejected", "cancelled"})


def validate_status_transition(
    settlement: Settlement, new_status: str, actor_id: uuid.UUID
) -> None:
    """
    Durum geçişini doğrular.
    Geçersizse ValueError (iş hatası) veya PermissionError (yetki hatası) fırlatır.
    """
    if new_status not in _VALID_STATUSES:
        raise ValueError(f"Geçersiz durum. Geçerli durumlar: {', '.join(sorted(_VALID_STATUSES))}")

    if new_status in {"confirmed", "rejected"} and settlement.receiver_id != actor_id:
        raise PermissionError("Yalnızca alıcı bu işlemi yapabilir.")

    if new_status == "cancelled" and settlement.payer_id != actor_id:
        raise PermissionError("Yalnızca gönderen iptal edebilir.")


async def update_settlement_status(
    db: AsyncSession, settlement: Settlement, *, new_status: str
) -> Settlement:
    settlement.status = new_status
    if new_status == "confirmed" and settlement.settled_at is None:
        settlement.settled_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(settlement)
    return settlement
