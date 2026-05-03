from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.pagination import CursorPage, decode_cursor, encode_cursor
from src.modules.expenses.models import Expense, ExpenseSplit


async def get_by_id(db: AsyncSession, expense_id: uuid.UUID) -> Expense | None:
    result = await db.execute(
        select(Expense)
        .options(
            selectinload(Expense.splits).selectinload(ExpenseSplit.user),
            selectinload(Expense.group),
            selectinload(Expense.payer),
        )
        .where(Expense.id == expense_id, Expense.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_by_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    *,
    limit: int = 20,
    cursor: str | None = None,
) -> CursorPage[Expense]:
    filters = [Expense.group_id == group_id, Expense.deleted_at.is_(None)]

    if cursor:
        parts = decode_cursor(cursor)
        if parts and len(parts) == 2:
            cursor_date = date.fromisoformat(parts[0])
            cursor_id = uuid.UUID(parts[1])
            filters.append(
                or_(
                    Expense.expense_date < cursor_date,
                    and_(Expense.expense_date == cursor_date, Expense.id < cursor_id),
                )
            )

    result = await db.execute(
        select(Expense)
        .options(
            selectinload(Expense.splits).selectinload(ExpenseSplit.user),
            selectinload(Expense.group),
            selectinload(Expense.payer),
        )
        .where(*filters)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(limit + 1)
    )
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.expense_date.isoformat(), str(last.id))

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)


async def get_user_assigned(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    cursor: str | None = None,
    status: str = "all",
    group_id: uuid.UUID | None = None,
) -> CursorPage[Expense]:
    filters = [ExpenseSplit.user_id == user_id, Expense.deleted_at.is_(None)]

    if group_id is not None:
        filters.append(Expense.group_id == group_id)
    if status == "unpaid":
        filters.append(ExpenseSplit.owed_amount > ExpenseSplit.paid_amount)
    elif status == "paid":
        filters.append(ExpenseSplit.paid_amount >= ExpenseSplit.owed_amount)

    if cursor:
        parts = decode_cursor(cursor)
        if parts and len(parts) == 2:
            cursor_date = date.fromisoformat(parts[0])
            cursor_id = uuid.UUID(parts[1])
            filters.append(
                or_(
                    Expense.expense_date < cursor_date,
                    and_(Expense.expense_date == cursor_date, Expense.id < cursor_id),
                )
            )

    result = await db.execute(
        select(Expense)
        .join(ExpenseSplit, ExpenseSplit.expense_id == Expense.id)
        .options(selectinload(Expense.splits), selectinload(Expense.group), selectinload(Expense.payer))
        .where(*filters)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(limit + 1)
    )
    rows = list(result.scalars().unique().all())
    has_more = len(rows) > limit
    items = rows[:limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.expense_date.isoformat(), str(last.id))

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)


async def get_split_by_id(
    db: AsyncSession, split_id: uuid.UUID
) -> ExpenseSplit | None:
    result = await db.execute(
        select(ExpenseSplit).where(ExpenseSplit.id == split_id)
    )
    return result.scalars().first()
