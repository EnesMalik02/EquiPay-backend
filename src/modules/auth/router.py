import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.database import get_db
from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_refresh_token_from_request,
    verify_password,
)
from src.modules.auth import services
from src.modules.auth.schemas import TokenResponse, UserLoginRequest, UserRegisterRequest
from src.modules.users import services as user_services
from src.modules.users.models import User
from src.modules.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def set_tokens_in_response(request: Request, response: Response, user_id: str) -> TokenResponse:
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    if request.headers.get("x-platform") == "web":
        response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=30 * 60, samesite="lax")
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=7 * 24 * 60 * 60, samesite="lax")

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Kullanıcı Kayıt")
async def register(
    request: Request,
    data: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    if await services.get_user_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu email adresi zaten kayıtlı.")

    if await services.get_user_by_username(db, data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu kullanıcı adı zaten alınmış.")

    if await user_services.get_by_phone(db, data.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu telefon numarası zaten kayıtlı.")

    try:
        user = await services.create_user(
            db,
            email=data.email,
            password=data.password,
            phone=data.phone,
            username=data.username,
        )
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kayıt sırasında bir çakışma oluştu.")

    return set_tokens_in_response(request, response, str(user.id))


@router.post("/login", response_model=TokenResponse, summary="Kullanıcı Giriş")
async def login(
    request: Request,
    data: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await services.get_user_by_identifier(db, data.identifier)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email/kullanıcı adı veya şifre hatalı.")

    return set_tokens_in_response(request, response, str(user.id))


@router.post("/refresh", response_model=TokenResponse, summary="Refresh Token ile Yeni Access Token Alma")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = get_refresh_token_from_request(request)

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz refresh token türü veya içeriği.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token süresi dolmuş. Lütfen tekrar giriş yapın.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz refresh token.")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kullanıcı kimliği.")

    user = await services.get_user_by_id(db, user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı.")

    return set_tokens_in_response(request, response, str(user.id))


@router.get("/me", response_model=UserResponse, summary="Giriş Yapan Kullanıcı Bilgileri")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Çıkış Yap")
async def logout(request: Request, response: Response, current_user: User = Depends(get_current_user)):
    if request.headers.get("x-platform") == "web":
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
