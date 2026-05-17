from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_refresh_token_from_request,
)
from src.modules.auth import services
from src.modules.auth.schemas import TokenResponse, UserLoginRequest, UserRegisterRequest
from src.modules.users.models import User
from src.core.ratelimit import rate_limit
from src.modules.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def set_tokens_in_response(request: Request, response: Response, user_id: str) -> TokenResponse:
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    if request.headers.get("x-platform") == "web":
        response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=30 * 60, samesite="lax")
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=7 * 24 * 60 * 60, samesite="lax")

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Kullanıcı Kayıt", dependencies=[Depends(rate_limit("5/minute"))])
async def register(
    request: Request,
    data: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user_id = await services.register(db, email=data.email, password=data.password, username=data.username)
    return set_tokens_in_response(request, response, str(user_id))


@router.post("/login", response_model=TokenResponse, summary="User Login", dependencies=[Depends(rate_limit("10/minute"))])
async def login(
    request: Request,
    data: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user_id = await services.authenticate(db, data.identifier, data.password)
    return set_tokens_in_response(request, response, str(user_id))


@router.post("/refresh", response_model=TokenResponse, summary="Refresh Token ile Yeni Access Token Alma", dependencies=[Depends(rate_limit("20/minute"))])
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = get_refresh_token_from_request(request)
    user_id = await services.validate_refresh_token(db, token)
    return set_tokens_in_response(request, response, str(user_id))


@router.get("/me", response_model=UserResponse, summary="Giriş Yapan Kullanıcı Bilgileri", dependencies=[Depends(rate_limit("60/minute"))])
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Çıkış Yap", dependencies=[Depends(rate_limit("10/minute"))])
async def logout(request: Request, response: Response, current_user: User = Depends(get_current_user)):
    if request.headers.get("x-platform") == "web":
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
