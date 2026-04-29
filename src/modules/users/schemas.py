import re
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator

from src.core.schemas import ORMSchema

USERNAME_RE = re.compile(r'^[a-z0-9_]+$')


class UserResponse(ORMSchema):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None
    phone: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UpdateProfileRequest(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = None
    username: str | None = None
    phone: str | None = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str | None) -> str | None:
        if v is not None and not USERNAME_RE.match(v):
            raise ValueError("Kullanıcı adı yalnızca küçük İngilizce harf, rakam ve alt çizgi içerebilir.")
        return v


class UserSearchResult(ORMSchema):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None
