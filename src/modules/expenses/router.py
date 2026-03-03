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
    expense = await services.create_expense(
        db,
        group_id=data.group_id,
        paid_by=data.paid_by,
        title=data.title,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        expense_date=data.expense_date,
        created_by=current_user.id,
        splits=data.splits,
    )
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


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Masraf detayı")
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
    if expense.created_by != current_user.id:
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
    if expense.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca masrafı oluşturan silebilir.")
    await services.soft_delete_expense(db, expense)
