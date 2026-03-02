from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.core.database import get_db

from src.modules.users.models import User
from src.modules.users.schemas import UserResponse
from src.modules.auth.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse
from src.core.security import create_access_token, create_refresh_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

def set_tokens_in_response(response: Response, user_id: str):
    """Tokenları oluşturup response objesinde HttpOnly cookie olarak ayarlar ve return değeri olarak döndürür."""
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    
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
async def register(data: UserRegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Telefon numarası ve isim ile yeni bir kullanıcı kaydeder."""
    new_user = User(
        phone=data.phone,
        name=data.name
    )
    db.add(new_user)
    
    try:
        await db.commit()
        await db.refresh(new_user)
        return set_tokens_in_response(response, str(new_user.id))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon numarası ile kayıtlı bir kullanıcı zaten var."
        )

@router.post("/login", response_model=TokenResponse, summary="Kullanıcı Giriş")
async def login(data: UserLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Sadece telefon numarası ile giriş yapar. Kullanıcı yoksa 404 döner."""
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu telefon numarasına ait kullanıcı bulunamadı."
        )
        
    return set_tokens_in_response(response, str(user.id))

@router.get("/me", response_model=UserResponse, summary="Giriş Yapan Kullanıcı Bilgileri")
async def get_me(current_user: User = Depends(get_current_user)):
    """Aktif(oturum açmış) kullanıcının bilgilerini ve yetki durumunu döndürür."""
    return current_user
