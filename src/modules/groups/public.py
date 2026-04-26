"""
Groups modülünün dışarıya açık API'si.
Diğer modüller yalnızca bu dosyadan import yapabilir.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.groups import services


async def get_pending_invitation_group_ids(
    db: AsyncSession, user_id: uuid.UUID
) -> list[uuid.UUID]:
    return await services.get_pending_invitation_group_ids(db, user_id)
