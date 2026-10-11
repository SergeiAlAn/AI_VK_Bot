from dataclasses import dataclass

from config.settings import Settings
from keyboards.factory import KeyboardFactory
from services.ai.ai_service import AIService
from services.chat_service import ChatService
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from services.mode_registry import ModeRegistry
from services.user_service import UserService
from storage.json_repository import JsonUserRepository


@dataclass(frozen=True, slots=True)
class Container:
    """Контейнер зависимостей: собирается один раз при старте и передаётся в хендлеры."""

    settings: Settings
    repository: JsonUserRepository
    modes: ModeRegistry
    users: UserService
    dialogs: DialogService
    memory: MemoryService
    ai: AIService
    chat: ChatService
    keyboards: KeyboardFactory
