import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator

SPLIT_TYPES = {"equal", "exact", "percentage"}


# ── Expense ──

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
    paid_amount: Decimal | None = None


class ExpenseSplitResponse(BaseModel):
    id: uuid.UUID
    expense_id: uuid.UUID
    user_id: uuid.UUID
    owed_amount: Decimal
    paid_amount: Decimal
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseResponse(BaseModel):
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
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseDetailResponse(ExpenseResponse):
    splits: list[ExpenseSplitResponse] = []


class RecentExpenseResponse(ExpenseDetailResponse):
    group_name: str | None = None
