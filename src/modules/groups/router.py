import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.users.models import User
from src.modules.groups.schemas import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupMemberAdd,
    GroupMemberRoleUpdate,
    GroupMemberResponse,
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
    group = await services.create_group(
        db,
        name=data.name,
        description=data.description,
        created_by=current_user.id,
    )
    return group


@router.get("", response_model=list[GroupResponse], summary="Kullanıcının gruplarını listele", dependencies=[Depends(rate_limit("60/minute"))])
async def list_my_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_user_groups(db, current_user.id)


@router.get("/{group_id}", response_model=GroupResponse, summary="Grup detayı", dependencies=[Depends(rate_limit("60/minute"))])
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    return group


@router.patch("/{group_id}", response_model=GroupResponse, summary="Grubu güncelle", dependencies=[Depends(rate_limit("30/minute"))])
async def update_group(
    group_id: uuid.UUID,
    data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    member = await services.get_member(db, group_id, current_user.id)
    if not member or member.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca admin güncelleyebilir.")
    return await services.update_group(db, group, name=data.name, description=data.description)


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
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")

    member = await services.get_member(db, group_id, current_user.id)
    if not member or member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yalnızca admin rolündeki üye grubu silebilir.",
        )
    try:
        await services.delete_group(db, group)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ── Leave Group ─────────────────────────────────────────────────────────

@router.post(
    "/{group_id}/leave",
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
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")

    try:
        result = await services.leave_group(db, group, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if result["action"] == "group_deleted":
        return {"detail": "Son üyesiniz; grup silindi."}
    return {"detail": "Gruptan başarıyla çıkıldı."}


# ── Member Role ──────────────────────────────────────────────────────────

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
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")

    requester = await services.get_member(db, group_id, current_user.id)
    if not requester or requester.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yalnızca admin rol değişikliği yapabilir.",
        )

    target = await services.get_member(db, group_id, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Üye bulunamadı.")

    return await services.update_member_role(db, target, role=data.role)


# ── Group Members ──

@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
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
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")

    try:
        return await services.add_member(
            db, group_id=group_id, phone=data.phone, email=data.email, role=data.role
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/{group_id}/members",
    response_model=list[GroupMemberResponse],
    summary="Grup üyelerini listele",
    dependencies=[Depends(rate_limit("60/minute"))],
)
async def list_members(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_members(db, group_id)
