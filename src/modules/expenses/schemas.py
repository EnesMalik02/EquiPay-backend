import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator

SPLIT_TYPES = {"equal", "exact", "percentage"}


# ── Input schemas ──

class ExpenseSplitInput(BaseModel):
    user_id: uuid.UUID
    owed_amount: Decimal


class ExpenseCreate(BaseModel):
    group_id: uuid.UUID | None = None
    paid_by: uuid.UUID
    title: str
    amount: Decimal
    currency: str = "TRY"
    notes: str | None = None
    expense_date: date | None = None
    split_type: str = "equal"
    splits: list[ExpenseSplitInput]

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Tutar sıfırdan büyük olmalıdır.")
        return v

    @field_validator("split_type")
    @classmethod
    def split_type_must_be_valid(cls, v: str) -> str:
        if v not in SPLIT_TYPES:
            raise ValueError(f"split_type şunlardan biri olmalıdır: {', '.join(SPLIT_TYPES)}")
        return v


class ExpenseUpdate(BaseModel):
    title: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    expense_date: date | None = None


class ExpenseSplitPayRequest(BaseModel):
    paid_amount: Decimal | None = None  # None = remaining full amount

    @field_validator("paid_amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Ödeme tutarı sıfırdan büyük olmalıdır.")
        return v


# ── Response schemas ──

class ExpenseSplitResponse(BaseModel):
    """Split detayı — expense detail sayfasında tüm split'ler için kullanılır."""
    id: uuid.UUID
    expense_id: uuid.UUID
    user_id: uuid.UUID
    owed_amount: Decimal
    paid_amount: Decimal

    class Config:
        from_attributes = True


class GroupBrief(BaseModel):
    group_id: uuid.UUID
    name: str


class PaidByBrief(BaseModel):
    name: str


class UserAmount(BaseModel):
    direction: str  # "debit" | "credit"
    amount: Decimal
    currency: str


class ExpenseResponse(BaseModel):
    """Temel expense bilgisi — grup expense listesi için."""
    id: uuid.UUID
    group_id: uuid.UUID | None = None
    paid_by: uuid.UUID
    title: str
    amount: Decimal
    currency: str
    notes: str | None = None
    expense_date: date | None = None
    split_type: str
    is_fully_paid: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ExpenseDetailResponse(ExpenseResponse):
    """Expense detayı — tüm split'lerle birlikte."""
    splits: list[ExpenseSplitResponse] = []


# ── New detail schemas ──

class GroupDetail(BaseModel):
    id: uuid.UUID
    name: str


class PaidByDetail(BaseModel):
    id: uuid.UUID
    name: str


class SplitUserBrief(BaseModel):
    id: uuid.UUID
    name: str
    avatar_url: str | None = None


class SplitDetailItem(BaseModel):
    id: uuid.UUID
    user: SplitUserBrief
    owed_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    status: str  # "paid" | "pending"


class ExpenseFullDetailResponse(BaseModel):
    id: uuid.UUID
    group: GroupDetail | None
    paid_by: PaidByDetail
    title: str
    amount: Decimal
    currency: str
    notes: str | None = None
    expense_date: date | None = None
    split_type: str
    created_at: datetime | None = None
    splits: list[SplitDetailItem] = []


class ExpenseWithMySplitResponse(BaseModel):
    id: uuid.UUID
    title: str
    group: GroupBrief | None
    paid_by: PaidByBrief
    created_at: datetime | None
    updated_at: datetime | None
    user_amount: UserAmount
