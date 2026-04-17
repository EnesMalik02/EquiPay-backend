from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_current_user
from src.modules.users.models import User
from src.modules.users.schemas import UserSearchResult

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/search", response_model=list[UserSearchResult], summary="Email ile kullanıcı ara")
async def search_users(
    email: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .where(
            User.email.ilike(f"%{email}%"),
            User.id != current_user.id,
            User.deleted_at.is_(None),
        )
        .limit(10)
    )
    return list(result.scalars().all())
