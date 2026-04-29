import base64
import hashlib
import hmac
from typing import Generic, TypeVar

from src.config import settings
from src.core.schemas import ORMSchema

T = TypeVar("T")

_SEP = "|"
_SIG_SEP = "."


class CursorPage(ORMSchema, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool


def encode_cursor(*values: str) -> str:
    payload = _SEP.join(values)
    b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = _sign(b64)
    return f"{b64}{_SIG_SEP}{sig}"


def decode_cursor(cursor: str) -> list[str] | None:
    try:
        b64, sig = cursor.rsplit(_SIG_SEP, 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(b64)):
        return None
    try:
        payload = base64.urlsafe_b64decode(b64.encode()).decode()
        return payload.split(_SEP)
    except Exception:
        return None


def _sign(b64: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        b64.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
