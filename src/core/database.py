# database.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import settings  # pydantic-settings ile yönetilen config


# ──────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # bağlantı kopuksa otomatik yenile
    pool_recycle=1800,         # 30 dk'da bir bağlantıyı yenile
    echo=settings.DB_ECHO,    # prod'da False olmalı
    connect_args={
        "statement_cache_size": 0,  # ⚠️ Supabase PgBouncer (port 6543) için zorunlu
    },
)

# ──────────────────────────────────────────────
# Session Factory
# ──────────────────────────────────────────────
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ──────────────────────────────────────────────
# Base Model
# ──────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ──────────────────────────────────────────────
# FastAPI Dependency
# ──────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# ──────────────────────────────────────────────
# Lifespan (tablo oluşturma + engine kapatma)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()