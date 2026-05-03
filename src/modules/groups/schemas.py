import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, model_validator

from src.core.schemas import ORMSchema


# ── Group ──

class GroupCreate(BaseModel):
    name: str
    description: str | None = None
    currency_code: str = "TRY"


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupResponse(ORMSchema):
    id: uuid.UUID
    name: str
    description: str | None = None
    currency_code: str


class GroupWithStatsResponse(GroupResponse):
    member_count: int
    balance_formatted: str
    balance_direction: str
    updated_at: datetime | None = None


# ── GroupMember ──

class GroupMemberAdd(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    role: str = "member"

    @model_validator(mode="after")
    def at_least_one_identifier_required(self) -> "GroupMemberAdd":
        if not self.email and not self.username:
            raise ValueError("email veya username alanlarından en az biri zorunludur.")
        return self


class GroupMemberRoleUpdate(BaseModel):
    role: str


class GroupMemberResponse(ORMSchema):
    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime | None = None
    left_at: datetime | None = None
    username: str | None = None
    display_name: str | None = None


class GroupMemberAddResponse(ORMSchema):
    user_id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    role: str
    status: str


class GroupInvitationRespond(BaseModel):
    action: str  # "accept" | "decline"


class GroupMemberListResponse(ORMSchema):
    user_id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    role: str
    status: str
