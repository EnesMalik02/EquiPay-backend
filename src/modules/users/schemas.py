import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    id: uuid.UUID
    phone: str
    name: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
