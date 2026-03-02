from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.core.database import get_db
from src.modules.users.models import User
from src.modules.users.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/first", response_model=UserResponse, summary="İlk kullanıcıyı getir")
async def get_first_user(db: AsyncSession = Depends(get_db)):
    """Veritabanındaki ilk kullanıcıyı döndürür."""
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı (Tablo boş)")
        
    return user
