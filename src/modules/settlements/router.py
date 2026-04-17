import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
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
    response_model=list[SettlementResponse],
    summary="Kullanıcının ödeme kayıtları",
)
async def list_my_settlements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_user_settlements(db, current_user.id)


@router.get(
    "/group/{group_id}",
    response_model=list[SettlementResponse],
    summary="Grubun ödeme kayıtları",
)
async def list_group_settlements(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_settlements(db, group_id)


@router.get("/{settlement_id}", response_model=SettlementResponse, summary="Ödeme detayı")
async def get_settlement(
    settlement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settlement = await services.get_settlement_by_id(db, settlement_id)
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ödeme kaydı bulunamadı.")
    return settlement


@router.patch(
    "/{settlement_id}/status",
    response_model=SettlementResponse,
    summary="Ödeme durumunu güncelle",
)
async def update_settlement_status(
    settlement_id: uuid.UUID,
    data: SettlementUpdateStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settlement = await services.get_settlement_by_id(db, settlement_id)
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ödeme kaydı bulunamadı.")

    try:
        services.validate_status_transition(settlement, data.status, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return await services.update_settlement_status(db, settlement, new_status=data.status)
