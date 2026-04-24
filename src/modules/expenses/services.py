import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.expenses import repository
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
    split_type: str = "equal",
    splits: list[ExpenseSplitInput],
) -> Expense:
    split_total = sum(s.owed_amount for s in splits)
    if abs(split_total - amount) > Decimal("0.01"):
        raise ValueError(f"Paylaşım toplamı ({split_total}) ile toplam tutar ({amount}) eşleşmiyor.")

    expense = Expense(
        group_id=group_id,
        paid_by=paid_by,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
        split_type=split_type,
    )
    db.add(expense)
    await db.flush()

    for s in splits:
        split = ExpenseSplit(
            expense_id=expense.id,
            user_id=s.user_id,
            owed_amount=s.owed_amount,
            paid_amount=s.owed_amount if s.user_id == paid_by else Decimal("0"),
        )
        db.add(split)

    await db.flush()
    return await repository.get_by_id(db, expense.id)


async def get_expense_by_id(
    db: AsyncSession, expense_id: uuid.UUID
) -> Expense | None:
    return await repository.get_by_id(db, expense_id)


async def get_group_expenses(
    db: AsyncSession,
    group_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[Expense]:
    return await repository.get_by_group(db, group_id, limit=limit, offset=offset)


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
    return await repository.get_by_id(db, expense.id)


async def update_as_owner(
    db: AsyncSession,
    expense: Expense,
    user_id: uuid.UUID,
    *,
    title: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    notes: str | None = None,
    expense_date=None,
) -> Expense:
    if expense.paid_by != user_id:
        raise PermissionError("Yalnızca masrafı oluşturan güncelleyebilir.")
    return await update_expense(
        db, expense,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
    )


async def delete_as_owner(
    db: AsyncSession, expense: Expense, user_id: uuid.UUID
) -> None:
    if expense.paid_by != user_id:
        raise PermissionError("Yalnızca masrafı oluşturan silebilir.")
    await soft_delete_expense(db, expense)


async def soft_delete_expense(db: AsyncSession, expense: Expense) -> None:
    expense.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def get_split_by_id(
    db: AsyncSession, split_id: uuid.UUID
) -> ExpenseSplit | None:
    return await repository.get_split_by_id(db, split_id)


async def get_user_assigned_expenses(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    status: str = "all",
) -> list[Expense]:
    return await repository.get_user_assigned(db, user_id, limit=limit, offset=offset, status=status)


async def pay_split(
    db: AsyncSession,
    split: ExpenseSplit,
    *,
    paid_amount: Decimal | None = None,
) -> ExpenseSplit:
    remaining = split.owed_amount - split.paid_amount
    if remaining <= 0:
        return split
    if paid_amount is not None and paid_amount > remaining:
        raise ValueError(f"Ödeme tutarı kalan borçtan ({remaining}) fazla olamaz.")
    split.paid_amount += paid_amount if paid_amount is not None else remaining
    await db.flush()
    await db.refresh(split)
    return split


# ── Bakiye sorguları (groups modülü tarafından kullanılır) ────────────────

async def get_user_outstanding_debt(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Decimal:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            )
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id == group_id,
            Expense.deleted_at.is_(None),
            ExpenseSplit.user_id == user_id,
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
    )
    return result.scalar() or Decimal("0")


async def get_user_outstanding_receivable(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Decimal:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            )
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id == group_id,
            Expense.deleted_at.is_(None),
            Expense.paid_by == user_id,
            ExpenseSplit.user_id != user_id,
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
    )
    return result.scalar() or Decimal("0")


async def has_unsettled_balance(db: AsyncSession, group_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            )
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id == group_id,
            Expense.deleted_at.is_(None),
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
    )
    return (result.scalar() or Decimal("0")) > Decimal("0")
