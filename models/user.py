from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from models.dialog import Dialog
from utils.time import utc_now

SCHEMA_VERSION = 1


class PendingAction(StrEnum):
    """Действие, для которого бот ждёт следующий текст пользователя."""

    RENAME_DIALOG = "rename_dialog"


class UserSettings(BaseModel):
    # Режим, с которым создаются новые диалоги (запоминается последний выбранный)
    default_mode: str


class UserState(BaseModel):
    """Состояние многошагового сценария (переживает перезапуск бота, т.к. лежит в JSON)."""

    pending_action: PendingAction | None = None
    target_dialog_id: str | None = None

    def reset(self) -> None:
        self.pending_action = None
        self.target_dialog_id = None


class UserProfile(BaseModel):
    """Корневой документ users/<user_id>.json."""

    schema_version: int = SCHEMA_VERSION
    user_id: int
    active_dialog_id: str | None = None
    settings: UserSettings
    state: UserState = Field(default_factory=UserState)
    dialogs: list[Dialog] = Field(default_factory=list)
    # Сквозной счётчик для названий «Диалог №N» (не уменьшается при удалении)
    dialogs_created: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def find_dialog(self, dialog_id: str) -> Dialog | None:
        return next((d for d in self.dialogs if d.id == dialog_id), None)

    @property
    def active_dialog(self) -> Dialog | None:
        return self.find_dialog(self.active_dialog_id) if self.active_dialog_id else None
