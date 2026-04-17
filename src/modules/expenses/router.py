import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import get_current_user
from src.modules.users.models import User
from src.modules.expenses.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseDetailResponse,
    RecentExpenseResponse,
    ExpenseSplitPayRequest,
    ExpenseSplitResponse,
)
from src.modules.expenses import services

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni masraf oluştur",
)
async def create_expense(
    data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        expense = await services.create_expense(
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return expense


@router.get(
    "/group/{group_id}",
    response_model=list[ExpenseResponse],
    summary="Grubun masraflarını listele",
)
async def list_group_expenses(
    group_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_expenses(db, group_id, limit=limit, offset=offset)


@router.get(
    "/me/splits",
    response_model=list[RecentExpenseResponse],
    summary="Kullanıcının split'i olan tüm harcamalar",
)
async def list_my_split_expenses(
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expenses = await services.get_user_assigned_expenses(db, current_user.id, limit=limit)
    return [
        RecentExpenseResponse.model_validate(exp, from_attributes=True).model_copy(
            update={"group_name": exp.group.name if exp.group else None}
        )
        for exp in expenses
    ]


@router.get(
    "/me/recent",
    response_model=list[RecentExpenseResponse],
    summary="Kullanıcının son harcamaları (tüm gruplar)",
)
async def list_recent_my_expenses(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expenses = await services.get_recent_user_expenses(db, current_user.id, limit=limit)
    return [
        RecentExpenseResponse.model_validate(exp, from_attributes=True).model_copy(
            update={"group_name": exp.group.name if exp.group else None}
        )
        for exp in expenses
    ]


@router.get("/{expense_id}", response_model=ExpenseDetailResponse, summary="Masraf detayı")
async def get_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expense = await services.get_expense_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Masraf bulunamadı.")
    return expense


@router.patch("/{expense_id}", response_model=ExpenseResponse, summary="Masrafı güncelle")
async def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expense = await services.get_expense_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Masraf bulunamadı.")
    if expense.paid_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca masrafı oluşturan güncelleyebilir.")
    return await services.update_expense(
        db,
        expense,
        title=data.title,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        expense_date=data.expense_date,
    )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Masrafı sil (soft)")
async def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expense = await services.get_expense_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Masraf bulunamadı.")
    if expense.paid_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca masrafı oluşturan silebilir.")
    await services.soft_delete_expense(db, expense)


@router.patch(
    "/{expense_id}/splits/{split_id}/pay",
    response_model=ExpenseSplitResponse,
    summary="Split'i ödenmiş olarak işaretle",
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
