import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)


class UserSearchResult(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)
