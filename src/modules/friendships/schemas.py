import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr

from src.core.schemas import ORMSchema


class FriendRequestCreate(BaseModel):
    email: EmailStr


class FriendRequestRespond(BaseModel):
    action: str  # 'accept' | 'reject'


class FriendUserInfo(ORMSchema):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    username: str | None = None


class FriendResponse(ORMSchema):
    friendship_id: uuid.UUID
    user: FriendUserInfo
    created_at: datetime | None = None


class FriendRequestResponse(ORMSchema):
    id: uuid.UUID
    requester: FriendUserInfo
    created_at: datetime | None = None


class FriendshipStatusResponse(ORMSchema):
    id: uuid.UUID
    status: str
