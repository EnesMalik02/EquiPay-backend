import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.pagination import CursorPage
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.expenses.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseWithMySplitResponse,
    ExpenseFullDetailResponse,
    ReceiptUploadResponse,
    ExpenseSplitPayRequest,
    ExpenseSplitResponse,
)
from src.modules.expenses import services
from src.modules.users.models import User

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post(
    "/receipt/upload-temp",
    response_model=ReceiptUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Expense oluşturmadan önce fiş yükle (geçici)",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def upload_temp_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    key, url = await services.upload_temp_receipt(content, file.content_type or "")
    return ReceiptUploadResponse(receipt_url=url, receipt_key=key)


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
    return await services.create_expense(
        db,
        group_id=data.group_id,
        paid_by=data.paid_by,
        title=data.title,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        expense_date=data.expense_date,
        split_type=data.split_type,
        category=data.category,
        receipt_key=data.receipt_key,
        splits=data.splits,
        current_user_id=current_user.id,
    )


@router.get(
    "/group/{group_id}",
    response_model=CursorPage[ExpenseWithMySplitResponse],
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
    page = await services.list_group_expenses(
        db, group_id, current_user.id, limit=limit, cursor=cursor
    )
    return CursorPage(
        items=[services.build_expense_with_my_split(exp, current_user.id) for exp in page.items],
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


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
        items=[services.build_expense_with_my_split(exp, current_user.id) for exp in page.items],
        next_cursor=page.next_cursor,
        has_more=page.has_more,
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
    exp = await services.get_expense(db, expense_id, current_user.id)
    return services.build_expense_full_detail(exp)


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
    return await services.update_expense(
        db, expense_id, current_user.id,
        title=data.title,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        expense_date=data.expense_date,
        category=data.category,
    )


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
    await services.delete_expense(db, expense_id, current_user.id)


@router.put(
    "/{expense_id}/receipt",
    response_model=ReceiptUploadResponse,
    summary="Fiş yükle veya değiştir",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def upload_receipt(
    expense_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    url = await services.upload_receipt_for_expense(
        db, expense_id, current_user.id, content, file.content_type or ""
    )
    return ReceiptUploadResponse(receipt_url=url)


@router.delete(
    "/{expense_id}/receipt",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Fişi sil",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def delete_receipt(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await services.delete_receipt_for_expense(db, expense_id, current_user.id)


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
    return await services.pay_split_for_user(
        db, expense_id, split_id, current_user.id, paid_amount=data.paid_amount
    )
