import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.groups.models import Group, GroupMember


async def create_group(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
    created_by: uuid.UUID,
) -> Group:
    group = Group(name=name, description=description, created_by=created_by)
    db.add(group)
    await db.flush()

    # Oluşturan kullanıcıyı admin olarak ekle
    admin_member = GroupMember(
        group_id=group.id, user_id=created_by, role="admin"
    )
    db.add(admin_member)
    await db.flush()
    await db.refresh(group)
    return group


async def get_group_by_id(
    db: AsyncSession, group_id: uuid.UUID
) -> Group | None:
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_groups(
    db: AsyncSession, user_id: uuid.UUID
) -> list[Group]:
    result = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.left_at.is_(None),
            Group.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def update_group(
    db: AsyncSession,
    group: Group,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Group:
    if name is not None:
        group.name = name
    if description is not None:
        group.description = description
    await db.flush()
    await db.refresh(group)
    return group


async def soft_delete_group(db: AsyncSession, group: Group) -> None:
    group.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def add_member(
    db: AsyncSession,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "member",
) -> GroupMember:
    member = GroupMember(group_id=group_id, user_id=user_id, role=role)
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def get_group_members(
    db: AsyncSession, group_id: uuid.UUID
) -> list[GroupMember]:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.left_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def remove_member(db: AsyncSession, member: GroupMember) -> None:
    member.left_at = datetime.now(timezone.utc)
    await db.flush()
