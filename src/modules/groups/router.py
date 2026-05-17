import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.ratelimit import rate_limit
from src.core.schemas import MessageResponse
from src.core.security import get_current_user
from src.modules.users.models import User
from src.core.pagination import CursorPage
from src.modules.groups.schemas import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupWithStatsResponse,
    GroupStatsResponse,
    GroupMemberAdd,
    GroupMemberRoleUpdate,
    GroupMemberResponse,
    GroupMemberAddResponse,
    GroupMemberListResponse,
    GroupInvitationRespond,
)
from src.modules.groups import services

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni grup oluştur",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def create_group(
    data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.create_group(
        db,
        name=data.name,
        description=data.description,
        created_by=current_user.id,
        currency_code=data.currency_code,
    )


@router.get("", response_model=CursorPage[GroupWithStatsResponse], summary="Kullanıcının gruplarını listele", dependencies=[Depends(rate_limit("60/minute"))])
async def list_my_groups(
    cursor: str | None = None,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_user_groups_with_stats(db, current_user.id, limit=limit, cursor=cursor)


@router.get("/{group_id}", response_model=GroupWithStatsResponse, summary="Grup detayı", dependencies=[Depends(rate_limit("60/minute"))])
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_with_stats(db, group_id, current_user.id)


@router.get(
    "/{group_id}/stats",
    response_model=GroupStatsResponse,
    summary="Grup istatistikleri",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def get_group_stats(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_stats(db, group_id, current_user.id)


@router.patch("/{group_id}", response_model=GroupResponse, summary="Grubu güncelle", dependencies=[Depends(rate_limit("30/minute"))])
async def update_group(
    group_id: uuid.UUID,
    data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.update_group(db, group_id, current_user.id, name=data.name, description=data.description)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Grubu sil",
    dependencies=[Depends(rate_limit("10/minute"))],
    description=(
        "Grubu siler (deleted_at doldurulur). "
        "Yalnızca admin yapabilir. "
        "Gruptaki tüm bakiyeler sıfır olmalıdır. "
        "expenses / settlements verileri olduğu gibi kalır."
    ),
)
async def delete_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await services.delete_group(db, group_id, current_user.id)


@router.post(
    "/{group_id}/leave",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Gruptan çık",
    dependencies=[Depends(rate_limit("10/minute"))],
    description=(
        "Kullanıcıyı gruptan çıkarır. "
        "Açık borç/alacak varsa 409 döner. "
        "Admin ise ve başka üye varsa önce admin ataması gerekir (409). "
        "Admin ise ve son üyeyse grup soft-delete edilir."
    ),
)
async def leave_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await services.leave_group(db, group_id, current_user.id)
    return MessageResponse(message=message)


@router.patch(
    "/{group_id}/members/{user_id}/role",
    response_model=GroupMemberResponse,
    summary="Üye rolünü güncelle",
    dependencies=[Depends(rate_limit("20/minute"))],
    description="Yalnızca admin başka bir üyenin rolünü değiştirebilir.",
)
async def update_member_role(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    data: GroupMemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.update_member_role(db, group_id, current_user.id, user_id, role=data.role)


@router.post(
    "/{group_id}/members",
    response_model=GroupMemberAddResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gruba üye ekle",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def add_member(
    group_id: uuid.UUID,
    data: GroupMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.add_member(
        db,
        group_id=group_id,
        invited_by=current_user.id,
        email=data.email,
        username=data.username,
        role=data.role,
    )


@router.get(
    "/{group_id}/members",
    response_model=list[GroupMemberListResponse],
    summary="Grup üyelerini listele",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_members(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_members(db, group_id)


@router.post(
    "/{group_id}/invitations/respond",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Grup davetini kabul et veya reddet",
    dependencies=[Depends(rate_limit("20/minute"))],
)
async def respond_to_invitation(
    group_id: uuid.UUID,
    data: GroupInvitationRespond,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await services.respond_to_invitation(
        db,
        group_id=group_id,
        user_id=current_user.id,
        accept=data.action == "accept",
    )
    return MessageResponse(message=message)
