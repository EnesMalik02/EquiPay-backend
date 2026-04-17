import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, model_validator


class FriendRequestCreate(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None

    @model_validator(mode="after")
    def email_or_phone_required(self) -> "FriendRequestCreate":
        if not self.email and not self.phone:
            raise ValueError("email veya phone alanlarından en az biri zorunludur.")
        return self


class FriendRequestRespond(BaseModel):
    action: str  # 'accept' | 'reject'


class FriendUserInfo(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None

    class Config:
        from_attributes = True


class FriendResponse(BaseModel):
    friendship_id: uuid.UUID
    user: FriendUserInfo
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class FriendRequestResponse(BaseModel):
    id: uuid.UUID
    requester: FriendUserInfo
    created_at: datetime | None = None

    class Config:
        from_attributes = True
