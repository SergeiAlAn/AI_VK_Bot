import asyncio
import contextlib
import logging
from types import TracebackType

from vkbottle import API

logger = logging.getLogger(__name__)

# VK показывает статус «печатает» ~10 секунд, поэтому обновляем его чаще
TYPING_REFRESH_SECONDS = 5.0


class ThinkingIndicator:
    """Показывает, что бот работает над ответом, пока ждём модель.

    * отправляет сообщение-статус «🤔 Думаю над ответом…»;
    * в фоне каждые несколько секунд обновляет статус «печатает…» (typing imitation);
    * по завершении удаляет сообщение-статус, чтобы в чате остался только ответ.

    Индикатор косметический, поэтому любые его ошибки только логируются и
    никогда не мешают отправке самого ответа.
    """

    def __init__(self, api: API, peer_id: int, status_text: str) -> None:
        self._api = api
        self._peer_id = peer_id
        self._status_text = status_text
        self._status_cmid: int | None = None
        self._typing_task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> "ThinkingIndicator":
        try:
            sent = await self._api.messages.send(
                peer_ids=[self._peer_id], message=self._status_text, random_id=0
            )
            if isinstance(sent, list) and sent:
                self._status_cmid = sent[0].conversation_message_id
        except Exception as exc:
            logger.warning("Не удалось отправить статус «думаю»: %s", exc)

        self._typing_task = asyncio.create_task(self._keep_typing())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._typing_task is not None:
            self._typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._typing_task

        if self._status_cmid is not None:
            try:
                await self._api.messages.delete(
                    peer_id=self._peer_id, cmids=[self._status_cmid], delete_for_all=True
                )
            except Exception as exc:
                logger.warning("Не удалось удалить статус «думаю»: %s", exc)

    async def _keep_typing(self) -> None:
        while True:
            try:
                await self._api.messages.set_activity(peer_id=self._peer_id, type="typing")
            except Exception as exc:
                logger.debug("Не удалось обновить статус «печатает»: %s", exc)
            await asyncio.sleep(TYPING_REFRESH_SECONDS)
