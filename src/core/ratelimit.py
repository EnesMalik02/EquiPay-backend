import jwt
from fastapi import HTTPException, Request, status
from limits import parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import MovingWindowRateLimiter

from src.config import settings

# ──────────────────────────────────────────────
# Storage & Strategy
# ──────────────────────────────────────────────
_storage = RedisStorage(f"async+{settings.REDIS_URL}")
_limiter = MovingWindowRateLimiter(_storage)


# ──────────────────────────────────────────────
# Key Resolver: UUID varsa UUID, yoksa IP
# ──────────────────────────────────────────────
def _resolve_identifier(request: Request) -> str:
    raw = request.headers.get("Authorization") or ""
    token = raw.removeprefix("Bearer ").strip() or request.cookies.get("access_token", "")

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            sub = payload.get("sub")
            if sub and payload.get("type") == "access":
                return f"user:{sub}"
        except jwt.PyJWTError:
            pass

    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


# ──────────────────────────────────────────────
# Dependency Factory
# ──────────────────────────────────────────────
def rate_limit(limit: str):
    """
    Kullanım:
        @router.post("/login", dependencies=[Depends(rate_limit("10/minute"))])
    """
    parsed = parse(limit)

    async def _dependency(request: Request) -> None:
        identifier = _resolve_identifier(request)
        scope = f"{request.method}:{request.url.path}"
        allowed = await _limiter.hit(parsed, scope, identifier)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çok fazla istek. Lütfen biraz sonra tekrar deneyin.",
            )

    return _dependency
