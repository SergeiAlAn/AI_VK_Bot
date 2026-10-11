import logging

from models.chat import ChatMessage, Role
from services.exceptions import DialogNotFoundError
from services.user_service import UserService

logger = logging.getLogger(__name__)


class MemoryService:
    """Краткосрочная память диалогов.

    Хранит в каждом диалоге не более max_history сообщений: при превышении
    самые старые удаляются автоматически (скользящее окно).
    """

    def __init__(self, users: UserService, max_history: int = 100) -> None:
        self._users = users
        self._max_history = max_history

    @property
    def max_history(self) -> int:
        return self._max_history

    async def get_history(self, user_id: int, dialog_id: str) -> list[ChatMessage]:
        profile = await self._users.get_profile(user_id)
        dialog = profile.find_dialog(dialog_id)
        if dialog is None:
            raise DialogNotFoundError(dialog_id)
        return dialog.messages[-self._max_history :]

    async def append_exchange(
        self, user_id: int, dialog_id: str, user_text: str, assistant_text: str
    ) -> bool:
        """Сохраняет пару «вопрос — ответ» одной транзакцией.

        Возвращает False, если диалог успели удалить, пока модель генерировала ответ.
        """
        async with self._users.session(user_id) as profile:
            dialog = profile.find_dialog(dialog_id)
            if dialog is None:
                logger.info("user=%s: диалог %s удалён до сохранения ответа", user_id, dialog_id)
                return False

            dialog.messages.extend(
                (
                    ChatMessage(role=Role.USER, content=user_text),
                    ChatMessage(role=Role.ASSISTANT, content=assistant_text),
                )
            )
            overflow = len(dialog.messages) - self._max_history
            if overflow > 0:
                del dialog.messages[:overflow]
            dialog.touch()
            return True

    async def clear(self, user_id: int, dialog_id: str) -> int:
        """Очищает историю диалога, возвращает количество удалённых сообщений."""
        async with self._users.session(user_id) as profile:
            dialog = profile.find_dialog(dialog_id)
            if dialog is None:
                raise DialogNotFoundError(dialog_id)
            removed = len(dialog.messages)
            dialog.messages.clear()
            dialog.touch()
            return removed
