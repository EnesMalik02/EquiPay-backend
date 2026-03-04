import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator


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
    splits: list[ExpenseSplitInput]

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Tutar sıfırdan büyük olmalıdır.")
        return v


class ExpenseUpdate(BaseModel):
    title: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    expense_date: date | None = None


class ExpenseSplitPayRequest(BaseModel):
    paid_amount: Decimal | None = None
    """Opsiyonel. Verilmezse owed_amount'un tamamı ödenmiş sayılır."""


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
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseDetailResponse(ExpenseResponse):
    splits: list[ExpenseSplitResponse] = []
