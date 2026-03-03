import uuid
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
) -> Settlement:
    settlement = Settlement(
        group_id=group_id,
        payer_id=payer_id,
        receiver_id=receiver_id,
        amount=amount,
        currency=currency,
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


async def update_settlement_status(
    db: AsyncSession, settlement: Settlement, *, new_status: str
) -> Settlement:
    settlement.status = new_status
    await db.flush()
    await db.refresh(settlement)
    return settlement
