import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user
from src.modules.users.models import User
from src.modules.groups.schemas import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupMemberAdd,
    GroupMemberResponse,
)
from src.modules.groups import services

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni grup oluştur",
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


@router.get("", response_model=list[GroupResponse], summary="Kullanıcının gruplarını listele")
async def list_my_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_user_groups(db, current_user.id)


@router.get("/{group_id}", response_model=GroupResponse, summary="Grup detayı")
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    return group


@router.patch("/{group_id}", response_model=GroupResponse, summary="Grubu güncelle")
async def update_group(
    group_id: uuid.UUID,
    data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await services.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    if group.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca grup sahibi güncelleyebilir.")
    return await services.update_group(db, group, name=data.name, description=data.description)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Grubu kalıcı olarak sil",
    description=(
        "Grubu kalıcı olarak siler. "
        "Yalnızca admin rolündeki üye yapabilir. "
        "Gruptaki tüm bakiyelerin sıfır olması gerekir. "
        "Bu işlem geri alınamaz."
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
        await services.hard_delete_group(db, group)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ── Leave Group ─────────────────────────────────────────────────────────

@router.post(
    "/{group_id}/leave",
    status_code=status.HTTP_200_OK,
    summary="Gruptan çık",
    description=(
        "Mevcut kullanıcıyı gruptan çıkarır. "
        "Gruptan çıkabilmek için bakiyenizin sıfır olması gerekir "
        "(kimseye borcunuz ya da alacağınız kalmamış olmalı). "
        "Çıktıktan sonra eski harcamalarda 'Eski Üye' olarak görünürsünüz."
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

    if group.created_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Grubun kurucusu gruptan çıkamaz. "
                "Önce başka bir üyeyi admin yapın ya da grubu silin."
            ),
        )

    try:
        await services.leave_group(db, group, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return {"detail": "Gruptan başarıyla çıkıldı."}


# ── Group Members ──

@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gruba üye ekle",
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

    result = await db.execute(select(User).where(User.phone == data.phone, User.deleted_at.is_(None)))
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu telefon numarasına kayıtlı kullanıcı bulunamadı.")

    return await services.add_member(db, group_id=group_id, user_id=target_user.id, role=data.role)


@router.get(
    "/{group_id}/members",
    response_model=list[GroupMemberResponse],
    summary="Grup üyelerini listele",
)
async def list_members(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.get_group_members(db, group_id)
