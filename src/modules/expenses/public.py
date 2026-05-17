import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.expenses import services


async def get_user_balances_for_groups(
    db: AsyncSession, group_ids: list[uuid.UUID], user_id: uuid.UUID
) -> dict[uuid.UUID, Decimal]:
    return await services.get_user_balances_for_groups(db, group_ids, user_id)


async def has_unsettled_balance(db: AsyncSession, group_id: uuid.UUID) -> bool:
    return await services.has_unsettled_balance(db, group_id)


async def get_user_outstanding_receivable(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Decimal:
    return await services.get_user_outstanding_receivable(db, group_id, user_id)


async def get_user_outstanding_debt(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Decimal:
    return await services.get_user_outstanding_debt(db, group_id, user_id)
