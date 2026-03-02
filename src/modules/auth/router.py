from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.core.database import get_db

from src.modules.users.models import User
from src.modules.users.schemas import UserResponse
from src.modules.auth.schemas import UserRegisterRequest, UserLoginRequest

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Kullanıcı Kayıt")
async def register(data: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Telefon numarası ve isim ile yeni bir kullanıcı kaydeder."""
    new_user = User(
        phone=data.phone,
        name=data.name
    )
    db.add(new_user)
    
    try:
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon numarası ile kayıtlı bir kullanıcı zaten var."
        )

@router.post("/login", response_model=UserResponse, summary="Kullanıcı Giriş")
async def login(data: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Sadece telefon numarası ile giriş yapar. Kullanıcı yoksa 404 döner."""
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu telefon numarasına ait kullanıcı bulunamadı."
        )
        
    return user
