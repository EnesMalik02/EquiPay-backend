from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import CursorPage, decode_cursor, encode_cursor
from src.modules.settlements.models import Settlement


async def get_by_id(db: AsyncSession, settlement_id: uuid.UUID) -> Settlement | None:
    result = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    )
    return result.scalars().first()


async def get_by_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    *,
    limit: int = 20,
    cursor: str | None = None,
) -> CursorPage[Settlement]:
    filters = [Settlement.group_id == group_id]

    if cursor:
        parts = decode_cursor(cursor)
        if parts and len(parts) == 2:
            cursor_dt = datetime.fromisoformat(parts[0])
            cursor_id = uuid.UUID(parts[1])
            filters.append(
                or_(
                    Settlement.created_at < cursor_dt,
                    and_(Settlement.created_at == cursor_dt, Settlement.id < cursor_id),
                )
            )

    result = await db.execute(
        select(Settlement)
        .where(*filters)
        .order_by(Settlement.created_at.desc(), Settlement.id.desc())
        .limit(limit + 1)
    )
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)


async def get_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    cursor: str | None = None,
) -> CursorPage[Settlement]:
    filters = [(Settlement.payer_id == user_id) | (Settlement.receiver_id == user_id)]

    if cursor:
        parts = decode_cursor(cursor)
        if parts and len(parts) == 2:
            cursor_dt = datetime.fromisoformat(parts[0])
            cursor_id = uuid.UUID(parts[1])
            filters.append(
                or_(
                    Settlement.created_at < cursor_dt,
                    and_(Settlement.created_at == cursor_dt, Settlement.id < cursor_id),
                )
            )

    result = await db.execute(
        select(Settlement)
        .where(*filters)
        .order_by(Settlement.created_at.desc(), Settlement.id.desc())
        .limit(limit + 1)
    )
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
