from pydantic import BaseModel, ConfigDict


class ORMSchema(BaseModel):
    """Base for all response schemas. Enables ORM mode globally."""
    model_config = ConfigDict(from_attributes=True)
