import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import encode_cursor, decode_cursor
from src.modules.currencies.formatting import format_balance
from src.modules.expenses import public as expenses_public
from src.modules.groups import repository
from src.modules.groups.models import Group, GroupMember
from src.modules.groups.schemas import (
    CategoryStat,
    GroupStatsResponse,
    MemberStat,
    MonthlyTrend,
)
from src.modules.notifications import public as notifications_public
from src.modules.users import public as users_public


# ── Group CRUD ───────────────────────────────────────────────────────────

async def create_group(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
    created_by: uuid.UUID,
    currency_code: str = "TRY",
) -> Group:
    group = Group(name=name, description=description, created_by=created_by, currency_code=currency_code)
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


async def get_user_groups_with_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 30,
    cursor: str | None = None,
) -> dict:
    limit = max(1, min(limit, 30))

    cursor_updated_at = None
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        if decoded and len(decoded) == 2:
            try:
                cursor_updated_at = datetime.fromisoformat(decoded[0])
                cursor_id = uuid.UUID(decoded[1])
            except (ValueError, AttributeError):
                pass

    groups = await repository.get_user_groups(
        db, user_id, limit=limit + 1,
        cursor_updated_at=cursor_updated_at, cursor_id=cursor_id
    )
    has_more = len(groups) > limit
    if has_more:
        groups = groups[:limit]

    if not groups:
        return {"items": [], "next_cursor": None, "has_more": False}

    group_ids = [g.id for g in groups]
    member_counts = await repository.get_active_member_counts(db, group_ids)
    balances = await expenses_public.get_user_balances_for_groups(db, group_ids, user_id)

    items = []
    for g in groups:
        raw = balances.get(g.id, Decimal("0"))
        formatted, direction = format_balance(raw, g.currency_code)
        items.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "currency_code": g.currency_code,
            "member_count": member_counts.get(g.id, 0),
            "balance_formatted": formatted,
            "balance_direction": direction,
            "updated_at": g.updated_at,
        })

    last = groups[-1]
    next_cursor = encode_cursor(last.updated_at.isoformat(), str(last.id)) if has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


async def get_group_with_stats(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    member_count = await repository.get_active_member_count(db, group_id)
    balances = await expenses_public.get_user_balances_for_groups(db, [group_id], user_id)
    raw = balances.get(group_id, Decimal("0"))
    formatted, direction = format_balance(raw, group.currency_code)
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "currency_code": group.currency_code,
        "member_count": member_count,
        "balance_formatted": formatted,
        "balance_direction": direction,
        "updated_at": group.updated_at,
    }


async def get_user_group_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    return await repository.get_user_group_ids(db, user_id)


async def get_pending_invitation_group_ids(
    db: AsyncSession, user_id: uuid.UUID
) -> list[uuid.UUID]:
    return await repository.get_pending_invitation_group_ids(db, user_id)


async def update_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Group:
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    member = await repository.get_member(db, group_id, user_id)
    if not member or member.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca admin güncelleyebilir.")
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
    email: str | None = None,
    username: str | None = None,
    user_id: uuid.UUID | None = None,
    role: str = "member",
) -> GroupMember:
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")

    if user_id is None:
        if email:
            user = await users_public.get_by_email(db, email)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu email adresine kayıtlı kullanıcı bulunamadı.")
        else:
            user = await users_public.get_by_username(db, username)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu kullanıcı adına kayıtlı kullanıcı bulunamadı.")
        user_id = user.id

    existing = await repository.get_existing_membership(db, group_id, user_id)
    if existing:
        if existing.left_at is None:
            if existing.status == "pending":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kullanıcıya davet gönderildi, yanıt bekleniyor.")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kullanıcı zaten bu grubun aktif üyesi.")
        existing.left_at = None
        existing.role = role
        existing.status = await _resolve_member_status(db, invited_by, user_id)
        await db.flush()
        if existing.status == "pending":
            await _send_invitation_notification(db, group=group, user_id=user_id, invited_by=invited_by)
        return await repository.get_member_with_user(db, existing.id)

    member_status = await _resolve_member_status(db, invited_by, user_id)
    member = GroupMember(group_id=group_id, user_id=user_id, role=role, status=member_status)
    db.add(member)
    await db.flush()
    if member_status == "pending":
        await _send_invitation_notification(db, group=group, user_id=user_id, invited_by=invited_by)
    return await repository.get_member_with_user(db, member.id)


async def _resolve_member_status(
    db: AsyncSession, invited_by: uuid.UUID, user_id: uuid.UUID
) -> str:
    return "pending"


async def _send_invitation_notification(
    db: AsyncSession,
    *,
    group: Group,
    user_id: uuid.UUID,
    invited_by: uuid.UUID,
) -> None:
    inviter = await users_public.get_by_id(db, invited_by)
    await notifications_public.send_group_invitation(
        db,
        user_id=user_id,
        group_id=group.id,
        group_name=group.name,
        invited_by_id=invited_by,
        invited_by_name=inviter.display_name or inviter.username if inviter else "",
    )


async def respond_to_invitation(
    db: AsyncSession,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    accept: bool,
) -> str:
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    member = await repository.get_pending_invitation(db, group_id, user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bekleyen bir grup daveti bulunamadı.")
    if accept:
        member.status = "active"
        await db.flush()
        return "Gruba katıldınız."
    member.left_at = datetime.now(timezone.utc)
    await db.flush()
    return "Davet reddedildi."


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
    db: AsyncSession,
    group_id: uuid.UUID,
    requester_id: uuid.UUID,
    target_user_id: uuid.UUID,
    *,
    role: str,
) -> GroupMember:
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    requester = await repository.get_member(db, group_id, requester_id)
    if not requester or requester.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca admin rol değişikliği yapabilir.")
    target = await repository.get_member(db, group_id, target_user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Üye bulunamadı.")
    target.role = role
    await db.flush()
    await db.refresh(target)
    return target


# ── Group lifecycle ──────────────────────────────────────────────────────

async def delete_group(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    member = await repository.get_member(db, group_id, user_id)
    if not member or member.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yalnızca admin rolündeki üye grubu silebilir.")
    if await expenses_public.has_unsettled_balance(db, group_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Grupta açık borçlar var. Önce tüm bakiyeleri kapatın.")
    await soft_delete_group(db, group)


async def leave_group(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> str:
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")

    receivable = await expenses_public.get_user_outstanding_receivable(db, group_id, user_id)
    debt = await expenses_public.get_user_outstanding_debt(db, group_id, user_id)

    if receivable != Decimal("0") or debt != Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Gruptan çıkabilmek için bakiyenizin sıfır olması gerekir. Alacak: {receivable}, Borç: {debt}",
        )

    member = await repository.get_member(db, group_id, user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu grupta aktif üyeliğiniz bulunamadı.")

    if member.role == "admin":
        active_count = await repository.get_active_member_count(db, group_id)
        if active_count > 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Gruptan çıkmadan önce başka bir üyeye admin rolü atayın.")
        member.left_at = datetime.now(timezone.utc)
        await soft_delete_group(db, group)
        return "Son üyesiniz; grup silindi."

    member.left_at = datetime.now(timezone.utc)
    await db.flush()
    return "Gruptan başarıyla çıkıldı."


async def get_group_stats(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> GroupStatsResponse:
    from src.modules.groups import public as groups_public
    await groups_public.require_group_member(db, group_id, user_id)
    group = await repository.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grup bulunamadı.")
    stats = await repository.get_group_stats(db, group_id)
    return GroupStatsResponse(
        total_amount=stats["total_amount"],
        total_expense_count=stats["total_expense_count"],
        currency=group.currency_code,
        member_stats=[
            MemberStat(
                user_id=r.user_id,
                name=r.name,
                avatar_url=r.avatar_url,
                total_paid=r.total_paid,
                total_owed=r.total_owed,
                net_balance=r.net_balance,
                outstanding_debt=r.outstanding_debt,
                outstanding_receivable=r.outstanding_receivable,
            )
            for r in stats["member_stats"]
        ],
        category_breakdown=[
            CategoryStat(category=r.category, total=r.total, count=r.count)
            for r in stats["category_breakdown"]
        ],
        monthly_trend=[
            MonthlyTrend(year_month=r.year_month, total=r.total, count=r.count)
            for r in stats["monthly_trend"]
        ],
    )
