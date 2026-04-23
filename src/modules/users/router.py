from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.ratelimit import rate_limit
from src.core.security import get_current_user
from src.modules.users import services
from src.modules.users.models import User
from src.modules.users.schemas import UpdateProfileRequest, UserResponse, UserSearchResult

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me", response_model=UserResponse, summary="Profil güncelle")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.update_profile(
        db,
        current_user,
        email=body.email,
        display_name=body.display_name,
        username=body.username,
        phone=body.phone,
    )


@router.get("/search", response_model=list[UserSearchResult], summary="Email ile kullanıcı ara", dependencies=[Depends(rate_limit("30/minute"))])
async def search_users(
    email: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await services.search_by_email(db, email, exclude_id=current_user.id)
