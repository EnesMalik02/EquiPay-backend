import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class FriendRequestCreate(BaseModel):
    email: EmailStr


class FriendRequestRespond(BaseModel):
    action: str  # 'accept' | 'reject'


class FriendUserInfo(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FriendResponse(BaseModel):
    friendship_id: uuid.UUID
    user: FriendUserInfo
    created_at: datetime | None = None


class FriendRequestResponse(BaseModel):
    id: uuid.UUID
    requester: FriendUserInfo
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
