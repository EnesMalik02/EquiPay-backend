import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.groups.models import Group, GroupMember


async def get_by_id(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_groups(db: AsyncSession, user_id: uuid.UUID) -> list[Group]:
    result = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.left_at.is_(None),
            GroupMember.status == "active",
            Group.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def get_user_group_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(GroupMember.group_id).where(
            GroupMember.user_id == user_id,
            GroupMember.left_at.is_(None),
            GroupMember.status == "active",
        )
    )
    return list(result.scalars().all())


async def get_members(db: AsyncSession, group_id: uuid.UUID) -> list[GroupMember]:
    result = await db.execute(
        select(GroupMember)
        .options(selectinload(GroupMember.user))
        .where(
            GroupMember.group_id == group_id,
            GroupMember.left_at.is_(None),
            GroupMember.status == "active",
        )
    )
    return list(result.scalars().all())


async def get_member(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> GroupMember | None:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.left_at.is_(None),
            GroupMember.status == "active",
        )
    )
    return result.scalars().first()


async def get_pending_invitation(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> GroupMember | None:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.left_at.is_(None),
            GroupMember.status == "pending",
        )
    )
    return result.scalars().first()


async def get_member_with_user(
    db: AsyncSession, member_id: uuid.UUID
) -> GroupMember | None:
    result = await db.execute(
        select(GroupMember)
        .options(selectinload(GroupMember.user))
        .where(GroupMember.id == member_id)
    )
    return result.scalars().first()


async def get_existing_membership(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> GroupMember | None:
    """left_at dahil her türlü üyelik kaydını döndürür (yeniden ekleme için)."""
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    return result.scalars().first()


async def get_active_member_count(db: AsyncSession, group_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(GroupMember)
        .where(
            GroupMember.group_id == group_id,
            GroupMember.left_at.is_(None),
            GroupMember.status == "active",
        )
    )
    return result.scalar() or 0
