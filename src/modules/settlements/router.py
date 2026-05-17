import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.pagination import CursorPage
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.users.models import User
from src.modules.settlements.schemas import (
    SettlementCreate,
    SettlementUpdateStatus,
    SettlementResponse,
)
from src.modules.settlements import services

router = APIRouter(prefix="/settlements", tags=["Settlements"])


@router.post(
    "",
    response_model=SettlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni ödeme kaydı oluştur",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def create_settlement(
    data: SettlementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.create_settlement(
        db,
        group_id=data.group_id,
        payer_id=current_user.id,
        receiver_id=data.receiver_id,
        amount=data.amount,
        currency=data.currency,
        note=data.note,
    )


@router.get(
    "/me",
    response_model=CursorPage[SettlementResponse],
    summary="Kullanıcının ödeme kayıtları (sayfalı)",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_my_settlements(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_user_settlements(
        db, current_user.id, limit=limit, cursor=cursor
    )


@router.get(
    "/group/{group_id}",
    response_model=CursorPage[SettlementResponse],
    summary="Grubun ödeme kayıtları (sayfalı)",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_group_settlements(
    group_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_settlements(
        db, group_id, limit=limit, cursor=cursor
    )


@router.get("/{settlement_id}", response_model=SettlementResponse, summary="Ödeme detayı", dependencies=[Depends(rate_limit("60/minute"))])
async def get_settlement(
    settlement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_settlement_by_id(db, settlement_id)


@router.patch(
    "/{settlement_id}/status",
    response_model=SettlementResponse,
    summary="Ödeme durumunu güncelle",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def update_settlement_status(
    settlement_id: uuid.UUID,
    data: SettlementUpdateStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settlement = await services.get_settlement_by_id(db, settlement_id)
    return await services.apply_status_update(db, settlement, data.status, current_user.id)
