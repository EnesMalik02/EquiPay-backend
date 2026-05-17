import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.notifications import repository


async def send_group_invitation(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    group_name: str,
    invited_by_id: uuid.UUID,
    invited_by_name: str,
) -> None:
    await repository.create(
        db,
        user_id=user_id,
        type="group_invitation",
        data={
            "group_id": str(group_id),
            "group_name": group_name,
            "invited_by_id": str(invited_by_id),
            "invited_by_name": invited_by_name,
        },
    )
