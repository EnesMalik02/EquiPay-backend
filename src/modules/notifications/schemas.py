import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    data: dict | None = None
    is_read: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True
