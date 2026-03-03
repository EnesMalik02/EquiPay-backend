import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ── Group ──

class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    created_by: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── GroupMember ──

class GroupMemberAdd(BaseModel):
    phone: str
    role: str = "member"


class GroupMemberResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime | None = None
    left_at: datetime | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)
