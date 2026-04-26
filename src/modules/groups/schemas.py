import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, model_validator


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

    class Config:
        from_attributes = True


class GroupWithStatsResponse(GroupResponse):
    member_count: int
    balance: Decimal
    updated_at: datetime | None = None


# ── GroupMember ──

class GroupMemberAdd(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    username: str | None = None
    role: str = "member"

    @model_validator(mode="after")
    def at_least_one_identifier_required(self) -> "GroupMemberAdd":
        if not self.phone and not self.email and not self.username:
            raise ValueError("phone, email veya username alanlarından en az biri zorunludur.")
        return self


class GroupMemberRoleUpdate(BaseModel):
    role: str


class GroupMemberResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime | None = None
    left_at: datetime | None = None
    username: str | None = None
    display_name: str | None = None

    class Config:
        from_attributes = True


class GroupMemberAddResponse(BaseModel):
    user_id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    role: str
    status: str

    class Config:
        from_attributes = True


class GroupInvitationRespond(BaseModel):
    action: str  # "accept" | "decline"


class GroupMemberListResponse(BaseModel):
    user_id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    role: str

    class Config:
        from_attributes = True
