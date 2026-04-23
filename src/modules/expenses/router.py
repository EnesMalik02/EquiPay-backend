import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.expenses.models import Expense
from src.modules.expenses.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseDetailResponse,
    ExpenseWithMySplitResponse,
    MySplitSummary,
    ExpenseSplitPayRequest,
    ExpenseSplitResponse,
)
from src.modules.expenses import services
from src.modules.users.models import User
from src.services import expense_queries

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def _build_with_my_split(exp: Expense, user_id: uuid.UUID) -> ExpenseWithMySplitResponse:
    my_split_orm = next((s for s in exp.splits if s.user_id == user_id), None)
    return ExpenseWithMySplitResponse(
        id=exp.id,
        group_id=exp.group_id,
        group_name=exp.group.name if exp.group else None,
        paid_by=exp.paid_by,
        title=exp.title,
        amount=exp.amount,
        currency=exp.currency,
        notes=exp.notes,
        expense_date=exp.expense_date,
        is_fully_paid=exp.is_fully_paid,
        my_split=MySplitSummary(
            id=my_split_orm.id,
            owed_amount=my_split_orm.owed_amount,
            paid_amount=my_split_orm.paid_amount,
        ) if my_split_orm else None,
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
    response_model=list[ExpenseResponse],
    summary="Grubun masraflarını listele",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_group_expenses(
    group_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await expense_queries.list_group_expenses(
            db, group_id, current_user.id, limit=limit, offset=offset
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get(
    "/me/splits",
    response_model=list[ExpenseWithMySplitResponse],
    summary="Kullanıcının split'i olan harcamalar (sayfalı)",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_my_split_expenses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str = Query(default="all", pattern="^(all|pending|paid)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expenses = await services.get_user_assigned_expenses(
        db, current_user.id, limit=limit, offset=offset, status=status
    )
    return [_build_with_my_split(exp, current_user.id) for exp in expenses]


@router.get(
    "/{expense_id}",
    response_model=ExpenseDetailResponse,
    summary="Masraf detayı",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def get_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await expense_queries.get_expense(db, expense_id, current_user.id)
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
    return await services.pay_split(db, split, paid_amount=data.paid_amount)
