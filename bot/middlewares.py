import logging
import time

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

from keyboards.payloads import Cmd
from services.user_service import UserService

logger = logging.getLogger("bot.events")


class OnlyUsersMiddleware(BaseMiddleware[Message]):
    """Отсекает сообщения от сообществ/ботов (from_id < 0) и служебные события."""

    async def pre(self) -> None:
        if self.event.from_id <= 0:
            self.stop("Сообщение не от пользователя")


class LoggingMiddleware(BaseMiddleware[Message]):
    """Логирует входящие события и время их обработки (без текста сообщений — приватность)."""

    _started_at: float | None = None

    async def pre(self) -> None:
        # Один экземпляр middleware живёт на всё событие (pre → хендлеры → post)
        self._started_at = time.perf_counter()

    async def post(self) -> None:
        elapsed = time.perf_counter() - self._started_at if self._started_at else 0.0
        payload = self.event.get_payload_json()
        cmd = payload.get("cmd") if isinstance(payload, dict) else None
        logger.info(
            "user=%s cmd=%s text_len=%d handlers=%d %.2fs",
            self.event.from_id,
            cmd or "-",
            len(self.event.text or ""),
            len(self.handlers),
            elapsed,
        )


def build_pending_reset_middleware(users: UserService) -> type[BaseMiddleware[Message]]:
    """Нажатие любой кнопки (кроме самого «Переименовать») отменяет ожидание ввода названия,
    иначе следующее сообщение пользователя неожиданно стало бы названием диалога."""

    class PendingResetMiddleware(BaseMiddleware[Message]):
        async def pre(self) -> None:
            payload = self.event.get_payload_json()
            if not isinstance(payload, dict) or payload.get("cmd") == Cmd.RENAME_DIALOG.value:
                return
            state = await users.get_state(self.event.from_id)
            if state.pending_action is not None:
                await users.clear_pending_action(self.event.from_id)

    return PendingResetMiddleware
