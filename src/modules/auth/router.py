from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
import jwt
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.core.database import get_db
from src.config import settings

from src.modules.users.models import User
from src.modules.users.schemas import UserResponse
from src.modules.auth.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse
from src.core.security import create_access_token, create_refresh_token, get_current_user, get_refresh_token_from_request

router = APIRouter(prefix="/auth", tags=["Auth"])

def set_tokens_in_response(request: Request, response: Response, user_id: str):
    """Tokenları oluşturur. İstek web'den geliyorsa HttpOnly cookie olarak ayarlar, değilse sadece JSON olarak döndürür."""
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    
    # İsteğin tarayıcıdan (web) gelip gelmediğini anlamak için custom header kontrolü
    is_web = request.headers.get("x-platform") == "web"
    
    if is_web:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=30 * 60, # 30 dk
            samesite="lax",
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60, # 7 gün
            samesite="lax",
        )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Kullanıcı Kayıt")
async def register(request: Request, data: UserRegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Telefon numarası ve isim ile yeni bir kullanıcı kaydeder."""
    new_user = User(
        username=data.username,
        phone=data.phone,
    )
    db.add(new_user)
    
    try:
        await db.commit()
        await db.refresh(new_user)
        return set_tokens_in_response(request, response, str(new_user.id))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon numarası ile kayıtlı bir kullanıcı zaten var."
        )

@router.post("/login", response_model=TokenResponse, summary="Kullanıcı Giriş")
async def login(request: Request, data: UserLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Sadece telefon numarası ile giriş yapar. Kullanıcı yoksa 404 döner."""
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu telefon numarasına ait kullanıcı bulunamadı."
        )
        
    return set_tokens_in_response(request, response, str(user.id))

@router.post("/refresh", response_model=TokenResponse, summary="Refresh Token ile Yeni Access Token Alma")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Mevcut (ve geçerli) refresh_token'ı kullanarak yeni bir access ve refresh token çifti oluşturur."""
    token = get_refresh_token_from_request(request)
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz refresh token türü veya içeriği.",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token süresi dolmuş. Lütfen tekrar giriş yapın.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz refresh token.",
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz kullanıcı kimliği.")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı.",
        )
        
    return set_tokens_in_response(request, response, str(user.id))

@router.get("/me", response_model=UserResponse, summary="Giriş Yapan Kullanıcı Bilgileri")
async def get_me(current_user: User = Depends(get_current_user)):
    """Aktif(oturum açmış) kullanıcının bilgilerini ve yetki durumunu döndürür."""
    return current_user
