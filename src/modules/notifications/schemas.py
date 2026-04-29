import uuid
from datetime import datetime

from src.core.schemas import ORMSchema


class NotificationResponse(ORMSchema):
    id: uuid.UUID
    type: str
    data: dict | None = None
    is_read: bool
    created_at: datetime | None = None
