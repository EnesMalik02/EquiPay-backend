"""Object storage facade for receipt files backed by Supabase Storage.

Design:
    - The DB persists an opaque **object key** (path within the bucket), never a URL.
      URLs are a presentation concern and are projected on read via `public_url`.
    - Each upload mints a fresh key (uuid-suffixed) so cached CDN/URL responses
      never mask a freshly uploaded file. Callers delete the previous key
      *after* persisting the new one to avoid orphaning valid data on flush failure.
    - Callers do not assemble paths; they go through `new_temp_key` /
      `new_receipt_key`. The on-disk layout stays a storage-module concern.
"""

from __future__ import annotations

import io
import uuid

import httpx
from PIL import Image

from src.config import settings

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}
MAX_SIZE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 2048
WEBP_QUALITY = 82

_UPLOAD_TIMEOUT_S = 30.0
_DELETE_TIMEOUT_S = 15.0


class StorageValidationError(ValueError):
    """Caller-supplied content is unacceptable (unsupported type, too large)."""


# ── Key construction ──────────────────────────────────────────────────────

def new_temp_key(ext: str) -> str:
    return f"uploads/{uuid.uuid4()}.{ext}"


def new_receipt_key(expense_id: str, ext: str) -> str:
    return f"expenses/{expense_id}/{uuid.uuid4()}.{ext}"


# ── URL projection ────────────────────────────────────────────────────────

def public_url(key: str | None) -> str | None:
    if not key:
        return None
    return (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/"
        f"{settings.SUPABASE_RECEIPT_BUCKET}/{key}"
    )


# ── Content normalization ─────────────────────────────────────────────────

def _to_webp(content: bytes) -> bytes:
    img = Image.open(io.BytesIO(content))

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=WEBP_QUALITY, method=4)
    return buf.getvalue()


def _normalize(content: bytes, content_type: str) -> tuple[bytes, str, str]:
    """Validate and (for images) re-encode as WebP. Returns (bytes, content_type, ext)."""
    if content_type not in ALLOWED_MIME:
        raise StorageValidationError(f"Desteklenmeyen dosya türü: {content_type}")
    if len(content) > MAX_SIZE_BYTES:
        raise StorageValidationError("Dosya boyutu 10MB'ı aşamaz.")
    if content_type == "application/pdf":
        return content, content_type, "pdf"
    return _to_webp(content), "image/webp", "webp"


# ── Raw object I/O ────────────────────────────────────────────────────────

def _object_url(key: str) -> str:
    return (
        f"{settings.SUPABASE_URL}/storage/v1/object/"
        f"{settings.SUPABASE_RECEIPT_BUCKET}/{key}"
    )


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"}


async def _put_object(key: str, content: bytes, content_type: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            _object_url(key),
            content=content,
            headers={
                **_auth_headers(),
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            timeout=_UPLOAD_TIMEOUT_S,
        )
        resp.raise_for_status()


async def delete_object(key: str | None) -> None:
    """Idempotent: no-op when key is None; ignores 404 from upstream."""
    if not key:
        return
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            _object_url(key),
            headers=_auth_headers(),
            timeout=_DELETE_TIMEOUT_S,
        )
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()


# ── High-level use cases ──────────────────────────────────────────────────

async def upload_temp_receipt(content: bytes, content_type: str) -> str:
    """Upload an unbound receipt (no expense yet). Returns the new object key."""
    content, content_type, ext = _normalize(content, content_type)
    key = new_temp_key(ext)
    await _put_object(key, content, content_type)
    return key


async def upload_expense_receipt(expense_id: str, content: bytes, content_type: str) -> str:
    """Upload a receipt bound to an expense. Returns the new object key.

    Each call produces a unique key; the caller deletes the previous key
    via `delete_object` after the new key has been persisted.
    """
    content, content_type, ext = _normalize(content, content_type)
    key = new_receipt_key(expense_id, ext)
    await _put_object(key, content, content_type)
    return key
