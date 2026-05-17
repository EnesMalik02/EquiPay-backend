"""
Groups modülünün dışarıya açık API'si.
Diğer modüller yalnızca bu dosyadan import yapabilir.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.groups import services


async def get_pending_invitation_group_ids(
    db: AsyncSession, user_id: uuid.UUID
) -> list[uuid.UUID]:
    return await services.get_pending_invitation_group_ids(db, user_id)


async def require_group_member(
    db: AsyncSession, group_id: uuid.UUID | None, user_id: uuid.UUID
) -> None:
    if not group_id:
        return
    member = await services.get_member(db, group_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu grubun üyesi değilsiniz.",
        )
