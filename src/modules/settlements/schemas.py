import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator


class SettlementCreate(BaseModel):
    group_id: uuid.UUID | None = None
    receiver_id: uuid.UUID
    amount: Decimal
    currency: str = "TRY"

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Tutar sıfırdan büyük olmalıdır.")
        return v


class SettlementUpdateStatus(BaseModel):
    status: str  # 'confirmed' | 'rejected' | 'cancelled'


class SettlementResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID | None = None
    payer_id: uuid.UUID
    receiver_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
