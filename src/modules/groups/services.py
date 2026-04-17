import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.groups.models import Group, GroupMember
from src.modules.expenses.models import Expense, ExpenseSplit


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


# ── Member CRUD ──────────────────────────────────────────────────────────

async def add_member(
    db: AsyncSession,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "member",
) -> GroupMember:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    existing = result.scalars().first()

    if existing:
        if existing.left_at is None:
            raise ValueError("Kullanıcı zaten bu grubun aktif üyesi.")
        existing.left_at = None
        existing.role = role
        await db.flush()
        await db.refresh(existing)
        return existing

    member = GroupMember(group_id=group_id, user_id=user_id, role=role)
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def get_group_members(db: AsyncSession, group_id: uuid.UUID) -> list[GroupMember]:
    result = await db.execute(
        select(GroupMember)
        .options(selectinload(GroupMember.user))
        .where(GroupMember.group_id == group_id, GroupMember.left_at.is_(None))
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
        )
    )
    return result.scalars().first()


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


# ── Balance helpers ──────────────────────────────────────────────────────

async def _get_user_outstanding_debt(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Decimal:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            )
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id == group_id,
            Expense.deleted_at.is_(None),
            ExpenseSplit.user_id == user_id,
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
    )
    return result.scalar() or Decimal("0")


async def _get_user_outstanding_receivable(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Decimal:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            )
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id == group_id,
            Expense.deleted_at.is_(None),
            Expense.paid_by == user_id,
            ExpenseSplit.user_id != user_id,
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
    )
    return result.scalar() or Decimal("0")


async def get_user_net_balance(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> Decimal:
    """Pozitif = alacaklı, Negatif = borçlu, 0 = dengede."""
    receivable = await _get_user_outstanding_receivable(db, group_id, user_id)
    debt = await _get_user_outstanding_debt(db, group_id, user_id)
    return receivable - debt


async def _has_any_unsettled_balance(db: AsyncSession, group_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(ExpenseSplit.owed_amount - ExpenseSplit.paid_amount),
                Decimal("0"),
            )
        )
        .join(Expense, Expense.id == ExpenseSplit.expense_id)
        .where(
            Expense.group_id == group_id,
            Expense.deleted_at.is_(None),
            ExpenseSplit.owed_amount > ExpenseSplit.paid_amount,
        )
    )
    total = result.scalar() or Decimal("0")
    return total > Decimal("0")


async def _count_active_members(db: AsyncSession, group_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.left_at.is_(None),
        )
    )
    return result.scalar() or 0


# ── Group lifecycle ──────────────────────────────────────────────────────

async def delete_group(db: AsyncSession, group: Group) -> None:
    """
    Grubu soft-delete yapar.
    Şart: Gruptaki tüm bakiyeler sıfır olmalı.
    Yalnızca admin çağırabilir (kontrol router'da).
    """
    if await _has_any_unsettled_balance(db, group.id):
        raise ValueError("Grupta açık borçlar var. Önce tüm bakiyeleri kapatın.")
    await soft_delete_group(db, group)


async def leave_group(db: AsyncSession, group: Group, user_id: uuid.UUID) -> dict:
    """
    Kullanıcıyı gruptan çıkarır.

    - Açık borç/alacak varsa ValueError.
    - Admin ise ve başka aktif üye varsa PermissionError.
    - Admin ise ve son üyeyse grubu soft-delete eder.
    - Normal üye ise left_at doldurulur.

    Döner: {"action": "left"} veya {"action": "group_deleted"}
    """
    receivable = await _get_user_outstanding_receivable(db, group.id, user_id)
    debt = await _get_user_outstanding_debt(db, group.id, user_id)

    if receivable != Decimal("0") or debt != Decimal("0"):
        raise ValueError(
            "Gruptan çıkabilmek için bakiyenizin sıfır olması gerekir. "
            f"Alacak: {receivable}, Borç: {debt}"
        )

    member = await get_member(db, group.id, user_id)
    if not member:
        raise LookupError("Bu grupta aktif üyeliğiniz bulunamadı.")

    if member.role == "admin":
        active_count = await _count_active_members(db, group.id)
        if active_count > 1:
            raise PermissionError("Gruptan çıkmadan önce başka bir üyeye admin rolü atayın.")
        member.left_at = datetime.now(timezone.utc)
        await soft_delete_group(db, group)
        return {"action": "group_deleted"}

    member.left_at = datetime.now(timezone.utc)
    await db.flush()
    return {"action": "left"}
