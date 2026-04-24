import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None
    phone: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = None
    username: str | None = None
    phone: str | None = None

    @field_validator("username")
    @classmethod
    def username_no_spaces(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("Kullanıcı adı boşluk içeremez.")
        return v


class UserSearchResult(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None

    class Config:
        from_attributes = True
