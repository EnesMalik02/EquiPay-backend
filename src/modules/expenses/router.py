import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.pagination import CursorPage
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.expenses.models import Expense
from src.modules.expenses.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseWithMySplitResponse,
    ExpenseFullDetailResponse,
    GroupBrief,
    GroupDetail,
    PaidByBrief,
    PaidByDetail,
    SplitUserBrief,
    SplitDetailItem,
    UserAmount,
    ExpenseSplitPayRequest,
    ExpenseSplitResponse,
)
from src.modules.expenses import services
from src.modules.users.models import User
from src.services import expense_queries

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def _build_with_my_split(exp: Expense, user_id: uuid.UUID) -> ExpenseWithMySplitResponse:
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
        created_at=exp.created_at,
        updated_at=my_split.updated_at if my_split else None,
        user_amount=UserAmount(
            direction=direction,
            amount=outstanding,
            currency=exp.currency,
        ),
    )


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni masraf oluştur",
    dependencies=[Depends(rate_limit("30/minute"))],
)
async def create_expense(
    data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await expense_queries.create_expense(
            db,
            group_id=data.group_id,
            paid_by=data.paid_by,
            title=data.title,
            amount=data.amount,
            currency=data.currency,
            notes=data.notes,
            expense_date=data.expense_date,
            split_type=data.split_type,
            splits=data.splits,
            current_user_id=current_user.id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/group/{group_id}",
    response_model=CursorPage[ExpenseResponse],
    summary="Grubun masraflarını listele",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_group_expenses(
    group_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await expense_queries.list_group_expenses(
            db, group_id, current_user.id, limit=limit, cursor=cursor
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get(
    "/me/splits",
    response_model=CursorPage[ExpenseWithMySplitResponse],
    summary="Kullanıcının split'i olan harcamalar (sayfalı)",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_my_split_expenses(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    status: str = Query(default="all", pattern="^(all|paid|unpaid)$"),
    group_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = await services.get_user_assigned_expenses(
        db, current_user.id, limit=limit, cursor=cursor, status=status, group_id=group_id
    )
    return CursorPage(
        items=[_build_with_my_split(exp, current_user.id) for exp in page.items],
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


def _build_expense_full_detail(exp: Expense) -> ExpenseFullDetailResponse:
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
        created_at=exp.created_at,
        splits=splits,
    )


@router.get(
    "/{expense_id}",
    response_model=ExpenseFullDetailResponse,
    summary="Masraf detayı",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def get_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        exp = await expense_queries.get_expense(db, expense_id, current_user.id)
        return _build_expense_full_detail(exp)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.patch(
    "/{expense_id}",
    response_model=ExpenseResponse,
    summary="Masrafı güncelle",
    dependencies=[Depends(rate_limit("30/minute"))],
)
async def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await expense_queries.update_expense(
            db, expense_id, current_user.id,
            title=data.title,
            amount=data.amount,
            currency=data.currency,
            notes=data.notes,
            expense_date=data.expense_date,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Masrafı sil (soft)",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await expense_queries.delete_expense(db, expense_id, current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.patch(
    "/{expense_id}/splits/{split_id}/pay",
    response_model=ExpenseSplitResponse,
    summary="Split'i ödenmiş olarak işaretle",
    dependencies=[Depends(rate_limit("30/minute"))],
)
async def pay_split(
    expense_id: uuid.UUID,
    split_id: uuid.UUID,
    data: ExpenseSplitPayRequest = ExpenseSplitPayRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    split = await services.get_split_by_id(db, split_id)
    if not split or split.expense_id != expense_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Split kaydı bulunamadı.")
    if split.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca kendi borcunuzu ödeyebilirsiniz.")
    try:
        return await services.pay_split(db, split, paid_amount=data.paid_amount)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
