import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator

from src.core.schemas import ORMSchema


class SettlementCreate(BaseModel):
    group_id: uuid.UUID | None = None
    receiver_id: uuid.UUID
    amount: Decimal
    currency: str = "TRY"
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Tutar sıfırdan büyük olmalıdır.")
        return v


class SettlementUpdateStatus(BaseModel):
    status: str  # 'confirmed' | 'rejected' | 'cancelled'


class SettlementResponse(ORMSchema):
    id: uuid.UUID
    group_id: uuid.UUID | None = None
    payer_id: uuid.UUID
    receiver_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    settled_at: datetime | None = None
    note: str | None = None
    created_at: datetime | None = None
