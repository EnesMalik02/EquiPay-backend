import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.expenses import services as expenses_services
from src.modules.friendships import repository as friendships_repository
from src.modules.groups import repository
from src.modules.groups.models import Group, GroupMember
from src.modules.notifications import repository as notifications_repository
from src.modules.users import services as users_services


# ── Group CRUD ───────────────────────────────────────────────────────────

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

    admin_member = GroupMember(group_id=group.id, user_id=created_by, role="admin")
    db.add(admin_member)
    await db.flush()
    await db.refresh(group)
    return group


async def get_group_by_id(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    return await repository.get_by_id(db, group_id)


async def get_user_groups(db: AsyncSession, user_id: uuid.UUID) -> list[Group]:
    return await repository.get_user_groups(db, user_id)


async def get_user_group_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Kullanıcının aktif üyesi olduğu grup id'lerini döndürür."""
    return await repository.get_user_group_ids(db, user_id)


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


# ── Member CRUD ──────────────────────────────────────────────────────────

async def add_member(
    db: AsyncSession,
    *,
    group_id: uuid.UUID,
    invited_by: uuid.UUID,
    phone: str | None = None,
    email: str | None = None,
    user_id: uuid.UUID | None = None,
    role: str = "member",
) -> GroupMember:
    """
    Gruba üye ekler. Davet eden ile davet edilen arkadaşsa direkt aktif,
    değilse pending durumunda eklenir ve bildirim gönderilir.
    """
    if user_id is None:
        if phone:
            user = await users_services.get_by_phone(db, phone)
            if not user:
                raise LookupError("Bu telefon numarasına kayıtlı kullanıcı bulunamadı.")
        else:
            user = await users_services.get_by_email(db, email)
            if not user:
                raise LookupError("Bu email adresine kayıtlı kullanıcı bulunamadı.")
        user_id = user.id

    existing = await repository.get_existing_membership(db, group_id, user_id)
    if existing:
        if existing.left_at is None:
            if existing.status == "pending":
                raise ValueError("Kullanıcıya davet gönderildi, yanıt bekleniyor.")
            raise ValueError("Kullanıcı zaten bu grubun aktif üyesi.")
        existing.left_at = None
        existing.role = role
        existing.status = await _resolve_member_status(db, invited_by, user_id)
        await db.flush()
        if existing.status == "pending":
            await _send_invitation_notification(db, group_id=group_id, user_id=user_id, invited_by=invited_by)
        return await repository.get_member_with_user(db, existing.id)

    status = await _resolve_member_status(db, invited_by, user_id)
    member = GroupMember(group_id=group_id, user_id=user_id, role=role, status=status)
    db.add(member)
    await db.flush()
    if status == "pending":
        await _send_invitation_notification(db, group_id=group_id, user_id=user_id, invited_by=invited_by)
    return await repository.get_member_with_user(db, member.id)


async def _resolve_member_status(
    db: AsyncSession, invited_by: uuid.UUID, user_id: uuid.UUID
) -> str:
    friendship = await friendships_repository.get_existing(db, invited_by, user_id)
    if friendship and friendship.status == "accepted":
        return "active"
    return "pending"


async def _send_invitation_notification(
    db: AsyncSession,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    invited_by: uuid.UUID,
) -> None:
    inviter = await users_services.get_by_id(db, invited_by)
    group = await repository.get_by_id(db, group_id)
    await notifications_repository.create(
        db,
        user_id=user_id,
        type="group_invitation",
        data={
            "group_id": str(group_id),
            "group_name": group.name if group else "",
            "invited_by_id": str(invited_by),
            "invited_by_name": inviter.display_name or inviter.username if inviter else "",
        },
    )


async def respond_to_invitation(
    db: AsyncSession,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    accept: bool,
) -> None:
    member = await repository.get_pending_invitation(db, group_id, user_id)
    if not member:
        raise LookupError("Bekleyen bir grup daveti bulunamadı.")
    if accept:
        member.status = "active"
        await db.flush()
    else:
        member.left_at = datetime.now(timezone.utc)
        await db.flush()


async def get_group_members(db: AsyncSession, group_id: uuid.UUID) -> list[GroupMember]:
    return await repository.get_members(db, group_id)


async def get_member(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> GroupMember | None:
    return await repository.get_member(db, group_id, user_id)


async def remove_member(db: AsyncSession, member: GroupMember) -> None:
    member.left_at = datetime.now(timezone.utc)
    await db.flush()


async def update_member_role(
    db: AsyncSession, member: GroupMember, *, role: str
) -> GroupMember:
    member.role = role
    await db.flush()
    await db.refresh(member)
    return member


# ── Group lifecycle ──────────────────────────────────────────────────────

async def delete_group(db: AsyncSession, group: Group) -> None:
    if await expenses_services.has_unsettled_balance(db, group.id):
        raise ValueError("Grupta açık borçlar var. Önce tüm bakiyeleri kapatın.")
    await soft_delete_group(db, group)


async def leave_group(db: AsyncSession, group: Group, user_id: uuid.UUID) -> dict:
    receivable = await expenses_services.get_user_outstanding_receivable(db, group.id, user_id)
    debt = await expenses_services.get_user_outstanding_debt(db, group.id, user_id)

    if receivable != Decimal("0") or debt != Decimal("0"):
        raise ValueError(
            "Gruptan çıkabilmek için bakiyenizin sıfır olması gerekir. "
            f"Alacak: {receivable}, Borç: {debt}"
        )

    member = await repository.get_member(db, group.id, user_id)
    if not member:
        raise LookupError("Bu grupta aktif üyeliğiniz bulunamadı.")

    if member.role == "admin":
        active_count = await repository.get_active_member_count(db, group.id)
        if active_count > 1:
            raise PermissionError("Gruptan çıkmadan önce başka bir üyeye admin rolü atayın.")
        member.left_at = datetime.now(timezone.utc)
        await soft_delete_group(db, group)
        return {"action": "group_deleted"}

    member.left_at = datetime.now(timezone.utc)
    await db.flush()
    return {"action": "left"}
