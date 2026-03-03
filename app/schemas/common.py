from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class IdResponse(BaseModel):
    id: int


class TimestampedModel(BaseModel):
    created_at: datetime

