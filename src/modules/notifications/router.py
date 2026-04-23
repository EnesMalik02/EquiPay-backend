import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.users.models import User
from src.modules.notifications import repository
from src.modules.notifications.schemas import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="Okunmamış bildirimleri listele",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await repository.get_unread(db, current_user.id)


@router.patch(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bildirimi okundu olarak işaretle",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    found = await repository.mark_read(db, notification_id, current_user.id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bildirim bulunamadı.")
