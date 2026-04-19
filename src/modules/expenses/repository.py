import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.expenses.models import Expense, ExpenseSplit
from src.modules.groups.models import GroupMember


async def get_by_id(db: AsyncSession, expense_id: uuid.UUID) -> Expense | None:
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(Expense.id == expense_id, Expense.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_by_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[Expense]:
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(Expense.group_id == group_id, Expense.deleted_at.is_(None))
        .order_by(Expense.expense_date.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_user_assigned(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[Expense]:
    result = await db.execute(
        select(Expense)
        .join(ExpenseSplit, ExpenseSplit.expense_id == Expense.id)
        .options(selectinload(Expense.splits), selectinload(Expense.group))
        .where(ExpenseSplit.user_id == user_id, Expense.deleted_at.is_(None))
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().unique().all())


async def get_recent_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 10,
) -> list[Expense]:
    """Kullanıcının aktif üyesi olduğu grupların son harcamalarını döndürür."""
    result = await db.execute(
        select(Expense)
        .join(GroupMember, GroupMember.group_id == Expense.group_id)
        .options(selectinload(Expense.splits), selectinload(Expense.group))
        .where(
            GroupMember.user_id == user_id,
            GroupMember.left_at.is_(None),
            Expense.deleted_at.is_(None),
        )
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().unique().all())


async def get_split_by_id(
    db: AsyncSession, split_id: uuid.UUID
) -> ExpenseSplit | None:
    result = await db.execute(
        select(ExpenseSplit).where(ExpenseSplit.id == split_id)
    )
    return result.scalars().first()
