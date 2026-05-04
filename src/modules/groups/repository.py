import uuid
from datetime import datetime

from sqlalchemy import func, select, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.groups.models import Group, GroupMember


async def get_by_id(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_groups(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 30,
    cursor_updated_at: datetime | None = None,
    cursor_id: uuid.UUID | None = None,
) -> list[Group]:
    query = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.left_at.is_(None),
            GroupMember.status == "active",
            Group.deleted_at.is_(None),
        )
        .order_by(Group.updated_at.desc(), Group.id.desc())
        .limit(limit)
    )
    if cursor_updated_at is not None and cursor_id is not None:
        query = query.where(
            or_(
                Group.updated_at < cursor_updated_at,
                and_(Group.updated_at == cursor_updated_at, Group.id < cursor_id),
            )
        )
    result = await db.execute(query)
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
            GroupMember.status.in_(["active", "pending"]),
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


async def get_pending_invitation_group_ids(
    db: AsyncSession, user_id: uuid.UUID
) -> list[uuid.UUID]:
    """Kullanıcının henüz yanıtlamadığı davetlerin group_id listesini döndürür."""
    result = await db.execute(
        select(GroupMember.group_id).where(
            GroupMember.user_id == user_id,
            GroupMember.status == "pending",
            GroupMember.left_at.is_(None),
        )
    )
    return list(result.scalars().all())


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


async def get_active_member_counts(
    db: AsyncSession, group_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    result = await db.execute(
        select(GroupMember.group_id, func.count().label("cnt"))
        .where(
            GroupMember.group_id.in_(group_ids),
            GroupMember.left_at.is_(None),
            GroupMember.status == "active",
        )
        .group_by(GroupMember.group_id)
    )
    return {row.group_id: row.cnt for row in result}


async def get_group_stats(db: AsyncSession, group_id: uuid.UUID) -> dict:
    member_sql = text("""
        WITH paid_stats AS (
            SELECT paid_by AS user_id, SUM(amount) AS total_paid
            FROM expenses
            WHERE group_id = :gid AND deleted_at IS NULL
            GROUP BY paid_by
        ),
        owed_stats AS (
            SELECT es.user_id, SUM(es.owed_amount) AS total_owed
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = :gid AND e.deleted_at IS NULL
            GROUP BY es.user_id
        ),
        outstanding_debt_stats AS (
            SELECT es.user_id,
                   SUM(es.owed_amount - es.paid_amount) AS outstanding_debt
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = :gid
              AND e.deleted_at IS NULL
              AND es.owed_amount > es.paid_amount
            GROUP BY es.user_id
        ),
        outstanding_recv_stats AS (
            SELECT e.paid_by AS user_id,
                   SUM(es.owed_amount - es.paid_amount) AS outstanding_receivable
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = :gid
              AND e.deleted_at IS NULL
              AND es.user_id != e.paid_by
              AND es.owed_amount > es.paid_amount
            GROUP BY e.paid_by
        )
        SELECT
            gm.user_id,
            COALESCE(u.display_name, u.username) AS name,
            u.avatar_url,
            COALESCE(ps.total_paid, 0)          AS total_paid,
            COALESCE(os.total_owed, 0)           AS total_owed,
            COALESCE(ps.total_paid, 0) - COALESCE(os.total_owed, 0) AS net_balance,
            COALESCE(ds.outstanding_debt, 0)     AS outstanding_debt,
            COALESCE(rs.outstanding_receivable, 0) AS outstanding_receivable
        FROM group_members gm
        JOIN users u ON u.id = gm.user_id
        LEFT JOIN paid_stats ps            ON ps.user_id = gm.user_id
        LEFT JOIN owed_stats os            ON os.user_id = gm.user_id
        LEFT JOIN outstanding_debt_stats ds ON ds.user_id = gm.user_id
        LEFT JOIN outstanding_recv_stats rs ON rs.user_id = gm.user_id
        WHERE gm.group_id = :gid
          AND gm.status = 'active'
          AND gm.left_at IS NULL
        ORDER BY net_balance DESC
    """)

    summary_sql = text("""
        SELECT
            COALESCE(SUM(amount), 0) AS total_amount,
            COUNT(*) AS total_expense_count
        FROM expenses
        WHERE group_id = :gid AND deleted_at IS NULL
    """)

    category_sql = text("""
        SELECT
            category,
            SUM(amount) AS total,
            COUNT(*) AS count
        FROM expenses
        WHERE group_id = :gid AND deleted_at IS NULL
        GROUP BY category
        ORDER BY total DESC
    """)

    trend_sql = text("""
        SELECT
            TO_CHAR(expense_date, 'YYYY-MM') AS year_month,
            SUM(amount)                      AS total,
            COUNT(*)                         AS count
        FROM expenses
        WHERE group_id = :gid
          AND deleted_at IS NULL
          AND expense_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months'
        GROUP BY year_month
        ORDER BY year_month
    """)

    member_rows = (await db.execute(member_sql, {"gid": group_id})).fetchall()
    summary_row = (await db.execute(summary_sql, {"gid": group_id})).fetchone()
    category_rows = (await db.execute(category_sql, {"gid": group_id})).fetchall()
    trend_rows = (await db.execute(trend_sql, {"gid": group_id})).fetchall()

    return {
        "total_amount": summary_row.total_amount,
        "total_expense_count": summary_row.total_expense_count,
        "member_stats": member_rows,
        "category_breakdown": category_rows,
        "monthly_trend": trend_rows,
    }
