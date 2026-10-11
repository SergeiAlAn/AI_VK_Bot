from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from utils.time import utc_now


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Одно сообщение истории диалога."""

    role: Role
    content: str
    timestamp: datetime = Field(default_factory=utc_now)
