from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from models.chat import ChatMessage
from utils.time import utc_now


def _new_dialog_id() -> str:
    # Короткий id, чтобы укладываться в лимит 255 байт на payload кнопки VK
    return uuid4().hex[:10]


class Dialog(BaseModel):
    """Независимый диалог: свой режим общения и своя история сообщений."""

    id: str = Field(default_factory=_new_dialog_id)
    title: str
    mode: str
    # True, пока пользователь сам не переименовал диалог: тогда название
    # можно автоматически сгенерировать из первого сообщения
    auto_title: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    messages: list[ChatMessage] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = utc_now()
