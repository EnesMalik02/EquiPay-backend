import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.expenses import repository
from src.modules.expenses.models import Expense, ExpenseSplit
from src.modules.expenses.schemas import (
    ExpenseSplitInput,
    ExpenseFullDetailResponse,
    ExpenseWithMySplitResponse,
    GroupBrief,
    GroupDetail,
    PaidByBrief,
    PaidByDetail,
    SplitDetailItem,
    SplitUserBrief,
    UserAmount,
)
from fastapi import HTTPException, status
from src.core.cache import cache, CacheKeys, CacheTTL
from src.modules.groups import public as groups_public
from src.services import storage

logger = logging.getLogger(__name__)


async def _create_expense(
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
    category: str | None = None,
    receipt_url: str | None = None,
    splits: list[ExpenseSplitInput],
) -> Expense:
    split_total = sum(s.owed_amount for s in splits)
    if abs(split_total - amount) > Decimal("0.01"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Paylaşım toplamı ({split_total}) ile toplam tutar ({amount}) eşleşmiyor.")

    expense = Expense(
        group_id=group_id,
        paid_by=paid_by,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
        split_type=split_type,
        category=category,
        receipt_url=receipt_url,
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
    cursor: str | None = None,
):
    return await repository.get_by_group(db, group_id, limit=limit, cursor=cursor)


async def _update_expense_fields(
    db: AsyncSession,
    expense: Expense,
    *,
    title: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    notes: str | None = None,
    expense_date=None,
    category: str | None = None,
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
    if category is not None:
        expense.category = category
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
    category: str | None = None,
) -> Expense:
    if expense.paid_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca masrafı oluşturan güncelleyebilir.")
    return await _update_expense_fields(
        db, expense,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
        category=category,
    )


async def delete_as_owner(
    db: AsyncSession, expense: Expense, user_id: uuid.UUID
) -> None:
    if expense.paid_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca masrafı oluşturan silebilir.")
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
    cursor: str | None = None,
    status: str = "all",
    group_id: uuid.UUID | None = None,
):
    return await repository.get_user_assigned(db, user_id, limit=limit, cursor=cursor, status=status, group_id=group_id)


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ödeme tutarı kalan borçtan ({remaining}) fazla olamaz.")
    split.paid_amount += paid_amount if paid_amount is not None else remaining
    split.updated_at = datetime.now(timezone.utc)
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


async def get_user_balances_for_groups(
    db: AsyncSession, group_ids: list[uuid.UUID], user_id: uuid.UUID
) -> dict[uuid.UUID, Decimal]:
    """Returns balance (receivable - debt) per group_id for the given user."""
    if not group_ids:
        return {}

    debt_result = await db.execute(
        select(
            Expense.group_id,
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            ).label("debt"),
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id.in_(group_ids),
            Expense.deleted_at.is_(None),
            ExpenseSplit.user_id == user_id,
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
        .group_by(Expense.group_id)
    )
    debts: dict[uuid.UUID, Decimal] = {row.group_id: row.debt for row in debt_result}

    recv_result = await db.execute(
        select(
            Expense.group_id,
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            ).label("recv"),
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id.in_(group_ids),
            Expense.deleted_at.is_(None),
            Expense.paid_by == user_id,
            ExpenseSplit.user_id != user_id,
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
        .group_by(Expense.group_id)
    )
    receivables: dict[uuid.UUID, Decimal] = {row.group_id: row.recv for row in recv_result}

    return {
        gid: receivables.get(gid, Decimal("0")) - debts.get(gid, Decimal("0"))
        for gid in group_ids
    }


# ── Orchestration (grup üyelik kontrolü + CRUD) ───────────────────────────

async def _get_expense_or_404(db: AsyncSession, expense_id: uuid.UUID) -> Expense:
    expense = await get_expense_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Masraf bulunamadı.")
    return expense


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
    category: str | None,
    receipt_key: str | None = None,
    splits: list[ExpenseSplitInput],
    current_user_id: uuid.UUID,
) -> Expense:
    await groups_public.require_group_member(db, group_id, current_user_id)
    receipt_url = storage.public_url(storage.temp_path(receipt_key)) if receipt_key else None
    expense = await _create_expense(
        db,
        group_id=group_id,
        paid_by=paid_by,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
        split_type=split_type,
        category=category,
        receipt_url=receipt_url,
        splits=splits,
    )
    if group_id:
        await cache.invalidate_group_detail(str(group_id))
        await cache.invalidate_group_stats(str(group_id))
    return expense


async def list_group_expenses(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: str | None = None,
):
    await groups_public.require_group_member(db, group_id, user_id)
    return await get_group_expenses(db, group_id, limit=limit, cursor=cursor)


async def get_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Expense:
    expense = await _get_expense_or_404(db, expense_id)
    await groups_public.require_group_member(db, expense.group_id, user_id)
    return expense


async def get_expense_detail(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ExpenseFullDetailResponse:
    key = CacheKeys.expense_detail(str(expense_id))
    cached = await cache.get_str(key)
    if cached:
        return ExpenseFullDetailResponse.model_validate_json(cached)

    expense = await _get_expense_or_404(db, expense_id)
    await groups_public.require_group_member(db, expense.group_id, user_id)
    response = build_expense_full_detail(expense)
    await cache.set_str(key, response.model_dump_json(), CacheTTL.EXPENSE_DETAIL)
    return response


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
    category: str | None,
) -> Expense:
    expense = await _get_expense_or_404(db, expense_id)
    await groups_public.require_group_member(db, expense.group_id, user_id)
    result = await update_as_owner(
        db, expense, user_id,
        title=title,
        amount=amount,
        currency=currency,
        notes=notes,
        expense_date=expense_date,
        category=category,
    )
    await cache.invalidate_expense_detail(str(expense_id))
    if expense.group_id:
        await cache.invalidate_group_detail(str(expense.group_id))
        await cache.invalidate_group_stats(str(expense.group_id))
    return result


async def delete_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    expense = await _get_expense_or_404(db, expense_id)
    await groups_public.require_group_member(db, expense.group_id, user_id)
    await delete_as_owner(db, expense, user_id)
    await cache.invalidate_expense_detail(str(expense_id))
    if expense.group_id:
        await cache.invalidate_group_detail(str(expense.group_id))
        await cache.invalidate_group_stats(str(expense.group_id))


async def upload_temp_receipt(content: bytes, content_type: str) -> tuple[str, str]:
    try:
        return await storage.upload_temp(content, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Temp receipt upload failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Dosya yüklenemedi: {exc}")


async def upload_receipt_for_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
    content: bytes,
    content_type: str,
) -> str:
    expense = await _get_expense_or_404(db, expense_id)
    await groups_public.require_group_member(db, expense.group_id, user_id)
    if expense.paid_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca masrafı oluşturan fiş yükleyebilir.")
    try:
        url = await storage.upload_receipt(str(expense_id), content, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Receipt upload failed for expense %s", expense_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Dosya yüklenemedi: {exc}")
    expense.receipt_url = url
    await db.flush()
    await cache.invalidate_expense_detail(str(expense_id))
    return url


async def delete_receipt_for_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    expense = await _get_expense_or_404(db, expense_id)
    await groups_public.require_group_member(db, expense.group_id, user_id)
    if expense.paid_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca masrafı oluşturan fişi silebilir.")
    await storage.delete_receipt(str(expense_id))
    expense.receipt_url = None
    await db.flush()
    await cache.invalidate_expense_detail(str(expense_id))


async def pay_split_for_user(
    db: AsyncSession,
    expense_id: uuid.UUID,
    split_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    paid_amount: Decimal | None = None,
) -> ExpenseSplit:
    split = await get_split_by_id(db, split_id)
    if not split or split.expense_id != expense_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Split kaydı bulunamadı.")
    if split.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca kendi borcunuzu ödeyebilirsiniz.")
    expense = await get_expense_by_id(db, expense_id)
    result = await pay_split(db, split, paid_amount=paid_amount)
    await cache.invalidate_expense_detail(str(expense_id))
    if expense and expense.group_id:
        await cache.invalidate_group_detail(str(expense.group_id))
        await cache.invalidate_group_stats(str(expense.group_id))
    return result


def build_expense_with_my_split(exp: Expense, user_id: uuid.UUID) -> ExpenseWithMySplitResponse:
    my_split = next((s for s in exp.splits if s.user_id == user_id), None)
    direction = "credit" if exp.paid_by == user_id else "debit"
    if direction == "credit":
        outstanding = sum(
            s.owed_amount - s.paid_amount
            for s in exp.splits
            if s.user_id != user_id and s.owed_amount > s.paid_amount
        )
    else:
        outstanding = (my_split.owed_amount - my_split.paid_amount) if my_split else Decimal("0")
    payer_name = exp.payer.display_name or exp.payer.username if exp.payer else ""
    return ExpenseWithMySplitResponse(
        id=exp.id,
        title=exp.title,
        amount=exp.amount,
        currency=exp.currency,
        expense_date=exp.expense_date,
        is_fully_paid=exp.is_fully_paid,
        split_id=my_split.id if my_split else None,
        group=GroupBrief(group_id=exp.group.id, name=exp.group.name) if exp.group else None,
        paid_by=PaidByBrief(name=payer_name),
        category=exp.category,
        created_at=exp.created_at,
        updated_at=my_split.updated_at if my_split else None,
        user_amount=UserAmount(
            direction=direction,
            amount=outstanding,
            currency=exp.currency,
        ),
    )


def build_expense_full_detail(exp: Expense) -> ExpenseFullDetailResponse:
    payer_name = exp.payer.display_name or exp.payer.username if exp.payer else ""
    splits = []
    for s in exp.splits:
        user = s.user
        user_name = (user.display_name or user.username) if user else ""
        remaining = s.owed_amount - s.paid_amount
        splits.append(SplitDetailItem(
            id=s.id,
            user=SplitUserBrief(
                id=s.user_id,
                name=user_name,
                avatar_url=user.avatar_url if user else None,
            ),
            owed_amount=s.owed_amount,
            paid_amount=s.paid_amount,
            remaining_amount=max(remaining, Decimal("0")),
            status="paid" if s.paid_amount >= s.owed_amount else "pending",
        ))
    return ExpenseFullDetailResponse(
        id=exp.id,
        group=GroupDetail(id=exp.group.id, name=exp.group.name) if exp.group else None,
        paid_by=PaidByDetail(id=exp.paid_by, name=payer_name),
        title=exp.title,
        amount=exp.amount,
        currency=exp.currency,
        notes=exp.notes,
        expense_date=exp.expense_date,
        split_type=exp.split_type,
        category=exp.category,
        receipt_url=exp.receipt_url,
        created_at=exp.created_at,
        splits=splits,
    )
