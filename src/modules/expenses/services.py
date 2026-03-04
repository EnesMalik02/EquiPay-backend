import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.expenses.models import Expense, ExpenseSplit
from src.modules.expenses.schemas import ExpenseSplitInput


async def create_expense(
    db: AsyncSession,
    *,
    group_id: uuid.UUID | None,
    paid_by: uuid.UUID,
    title: str,
    amount: Decimal,
    currency: str,
    notes: str | None,
    expense_date=None,
    splits: list[ExpenseSplitInput],
) -> Expense:
    expense = Expense(
        group_id=group_id,
        paid_by=paid_by,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
    )
    db.add(expense)
    await db.flush()

    for s in splits:
        split = ExpenseSplit(
            expense_id=expense.id,
            user_id=s.user_id,
            owed_amount=s.owed_amount,
            # Faturayı ödeyen kişinin kendi payı anında ödenmiş sayılır.
            paid_amount=s.owed_amount if s.user_id == paid_by else Decimal("0"),
        )
        db.add(split)

    await db.flush()

    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(Expense.id == expense.id)
    )
    return result.scalar_one()


async def get_expense_by_id(
    db: AsyncSession, expense_id: uuid.UUID
) -> Expense | None:
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(Expense.id == expense_id, Expense.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_group_expenses(
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


async def update_expense(
    db: AsyncSession,
    expense: Expense,
    *,
    title: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    notes: str | None = None,
    expense_date=None,
) -> Expense:
    if title is not None:
        expense.title = title
    if amount is not None:
        expense.amount = amount
    if currency is not None:
        expense.currency = currency
    if notes is not None:
        expense.notes = notes
    if expense_date is not None:
        expense.expense_date = expense_date
    await db.flush()

    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(Expense.id == expense.id)
    )
    return result.scalar_one()


async def soft_delete_expense(db: AsyncSession, expense: Expense) -> None:
    expense.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def get_split_by_id(
    db: AsyncSession, split_id: uuid.UUID
) -> ExpenseSplit | None:
    result = await db.execute(
        select(ExpenseSplit).where(ExpenseSplit.id == split_id)
    )
    return result.scalars().first()


async def pay_split(
    db: AsyncSession,
    split: ExpenseSplit,
    *,
    paid_amount: Decimal | None = None,
) -> ExpenseSplit:
    """paid_amount verilmezse tüm borcu ödenmiş olarak işaretler."""
    split.paid_amount = paid_amount if paid_amount is not None else split.owed_amount
    await db.flush()
    await db.refresh(split)
    return split
