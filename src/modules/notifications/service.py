import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.groups import public as groups_public
from src.modules.notifications import repository
from src.modules.notifications.models import Notification


async def get_active_notifications(
    db: AsyncSession, user_id: uuid.UUID
) -> list[Notification]:
    """
    Aktif bildirimleri döndürür:
    - Okunmamış tüm bildirimler
    - Okunmuş olsa da üyelik hâlâ pending olan group_invitation bildirimleri
    """
    unread = await repository.get_unread(db, user_id)

    pending_group_ids = await groups_public.get_pending_invitation_group_ids(db, user_id)
    if not pending_group_ids:
        return unread

    pending_str_ids = {str(gid) for gid in pending_group_ids}
    read_invitations = await repository.get_read_by_type(db, user_id, "group_invitation")
    seen_ids = {n.id for n in unread}

    for notif in read_invitations:
        if notif.id not in seen_ids and notif.data and notif.data.get("group_id") in pending_str_ids:
            unread.append(notif)

    unread.sort(key=lambda n: n.created_at, reverse=True)
    return unread
