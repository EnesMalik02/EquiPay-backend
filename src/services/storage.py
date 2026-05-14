import io

import httpx
from PIL import Image

from src.config import settings

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DIMENSION = 2048          # px — longest side
WEBP_QUALITY = 82             # good balance size/quality


def _object_url(path: str) -> str:
    return f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_RECEIPT_BUCKET}/{path}"


def public_url(path: str) -> str:
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_RECEIPT_BUCKET}/{path}"


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"}


def receipt_path(expense_id: str) -> str:
    return f"expenses/{expense_id}"


def temp_path(key: str) -> str:
    return f"uploads/{key}"


def _to_webp(content: bytes) -> bytes:
    """Convert image bytes to WebP. Resizes if longest side > MAX_DIMENSION."""
    img = Image.open(io.BytesIO(content))

    # Preserve transparency via RGBA; otherwise RGB
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    # Downscale if too large
    w, h = img.size
    if max(w, h) > MAX_DIMENSION:
        scale = MAX_DIMENSION / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=WEBP_QUALITY, method=4)
    return buf.getvalue()


async def _upload(path: str, content: bytes, content_type: str) -> str:
    """Raw upload to any path. Returns public URL."""
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            _object_url(path),
            content=content,
            headers={
                **_auth_headers(),
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
    return public_url(path)


def _prepare(content: bytes, content_type: str) -> tuple[bytes, str]:
    """Validate and convert image to WebP. Returns (content, content_type)."""
    if content_type not in ALLOWED_MIME:
        raise ValueError(f"Desteklenmeyen dosya türü: {content_type}")
    if len(content) > MAX_SIZE:
        raise ValueError("Dosya boyutu 10MB'ı aşamaz.")
    if content_type != "application/pdf":
        content = _to_webp(content)
        content_type = "image/webp"
    return content, content_type


async def upload_temp(content: bytes, content_type: str) -> tuple[str, str]:
    """
    Upload to a temporary path. Returns (receipt_key, public_url).
    Used before expense creation so the expense ID is not needed yet.
    """
    import uuid as _uuid
    content, content_type = _prepare(content, content_type)
    key = str(_uuid.uuid4())
    url = await _upload(temp_path(key), content, content_type)
    return key, url


async def upload_receipt(expense_id: str, content: bytes, content_type: str) -> str:
    """
    Upload receipt to Supabase Storage. Returns public URL. Overwrites if exists.
    Images are converted to WebP before upload. PDFs pass through unchanged.
    """
    content, content_type = _prepare(content, content_type)
    return await _upload(receipt_path(expense_id), content, content_type)


async def delete_receipt(expense_id: str) -> None:
    """Delete receipt from Supabase Storage. Ignores 404."""
    path = receipt_path(expense_id)
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            _object_url(path),
            headers=_auth_headers(),
            timeout=15.0,
        )
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()
