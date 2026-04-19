"""
Application layer — cross-module expense use cases.

Kural: modül servislerini çağırır, mantığını yeniden yazmaz.
  - Üyelik kontrolü  → groups modülü
  - Sahiplik kontrolü + CRUD → expenses modülü
  - Orchestration (sıralama, yönlendirme) → burada
"""
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.expenses import services as expense_services
from src.modules.expenses.models import Expense
from src.modules.expenses.schemas import ExpenseSplitInput
from src.modules.groups import services as group_services


async def _get_expense_or_404(db: AsyncSession, expense_id: uuid.UUID) -> Expense:
    expense = await expense_services.get_expense_by_id(db, expense_id)
    if not expense:
        raise LookupError("Masraf bulunamadı.")
    return expense


async def _require_group_member(
    db: AsyncSession, group_id: uuid.UUID | None, user_id: uuid.UUID
) -> None:
    if not group_id:
        return
    member = await group_services.get_member(db, group_id, user_id)
    if not member:
        raise PermissionError("Bu grubun üyesi değilsiniz.")


async def create_expense(
    db: AsyncSession,
    *,
    group_id: uuid.UUID | None,
    paid_by: uuid.UUID,
    title: str,
    amount: Decimal,
    currency: str,
    notes: str | None,
    expense_date,
    split_type: str,
    splits: list[ExpenseSplitInput],
    current_user_id: uuid.UUID,
) -> Expense:
    await _require_group_member(db, group_id, current_user_id)
    return await expense_services.create_expense(
        db,
        group_id=group_id,
        paid_by=paid_by,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
        split_type=split_type,
        splits=splits,
    )


async def list_group_expenses(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> list[Expense]:
    await _require_group_member(db, group_id, user_id)
    return await expense_services.get_group_expenses(db, group_id, limit=limit, offset=offset)


async def get_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Expense:
    expense = await _get_expense_or_404(db, expense_id)
    await _require_group_member(db, expense.group_id, user_id)
    return expense


async def update_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    title: str | None,
    amount: Decimal | None,
    currency: str | None,
    notes: str | None,
    expense_date,
) -> Expense:
    expense = await _get_expense_or_404(db, expense_id)
    await _require_group_member(db, expense.group_id, user_id)
    return await expense_services.update_as_owner(
        db, expense, user_id,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
    )


async def delete_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    expense = await _get_expense_or_404(db, expense_id)
    await _require_group_member(db, expense.group_id, user_id)
    await expense_services.delete_as_owner(db, expense, user_id)
