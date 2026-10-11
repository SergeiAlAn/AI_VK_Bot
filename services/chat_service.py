import logging
from dataclasses import dataclass, field

from config.prompts import FILE_OUTPUT_INSTRUCTIONS
from models.dialog import Dialog
from models.mode import ChatMode
from services.ai.ai_service import AIService
from services.dialog_service import DialogService
from services.exceptions import EmptyMessageError, MessageTooLongError, UserBusyError
from services.files import FileExtractor, GeneratedFile
from services.memory_service import MemoryService
from services.mode_registry import ModeRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChatReply:
    text: str
    dialog: Dialog
    mode: ChatMode
    model: str
    truncated: bool
    files: tuple[GeneratedFile, ...] = field(default_factory=tuple)


class ChatService:
    """Сценарий «пользователь задал вопрос → получил ответ модели».

    Не зависит от VK: тот же сервис можно использовать из Telegram-бота,
    веб-API или тестов.
    """

    def __init__(
        self,
        ai: AIService,
        dialogs: DialogService,
        memory: MemoryService,
        modes: ModeRegistry,
        max_input_chars: int,
        files: FileExtractor | None = None,
    ) -> None:
        self._ai = ai
        self._dialogs = dialogs
        self._memory = memory
        self._modes = modes
        self._max_input_chars = max_input_chars
        self._files = files or FileExtractor()
        self._in_progress: set[int] = set()

    def validate(self, text: str | None) -> str:
        text = (text or "").strip()
        if not text:
            raise EmptyMessageError
        if len(text) > self._max_input_chars:
            raise MessageTooLongError(len(text), self._max_input_chars)
        return text

    def is_busy(self, user_id: int) -> bool:
        return user_id in self._in_progress

    async def ask(self, user_id: int, text: str | None) -> ChatReply:
        """Бросает EmptyMessageError, MessageTooLongError, UserBusyError и AIError."""
        user_text = self.validate(text)
        if user_id in self._in_progress:
            raise UserBusyError
        self._in_progress.add(user_id)
        try:
            return await self._ask(user_id, user_text)
        finally:
            self._in_progress.discard(user_id)

    async def _ask(self, user_id: int, user_text: str) -> ChatReply:
        # Снимок активного диалога: долгий запрос к модели идёт без блокировки
        # профиля, чтобы пользователь мог пользоваться меню во время ожидания
        dialog = await self._dialogs.get_active(user_id)
        mode = self._modes.resolve(dialog.mode)
        history = dialog.messages[-self._memory.max_history :]

        response = await self._ai.generate_reply(
            system_prompt=mode.system_prompt + FILE_OUTPUT_INSTRUCTIONS,
            history=history,
            user_message=user_text,
        )

        # В историю пишется ответ вместе с файловыми блоками: так модель «помнит»
        # содержимое выданных файлов и может их дорабатывать по просьбе пользователя.
        # Ответ сохраняется в тот диалог, в котором был задан вопрос,
        # даже если пользователь успел переключиться на другой
        saved = await self._memory.append_exchange(user_id, dialog.id, user_text, response.content)
        if saved and dialog.auto_title:
            await self._dialogs.apply_auto_title(user_id, dialog.id, user_text)

        parsed = self._files.parse(response.content)
        if parsed.files:
            logger.info(
                "user=%s: модель выдала файлы %s", user_id, ", ".join(f.name for f in parsed.files)
            )

        return ChatReply(
            text=parsed.text,
            dialog=dialog,
            mode=mode,
            model=response.model,
            truncated=response.truncated,
            files=parsed.files,
        )

    def preview(self, raw: str) -> str:
        """Текст сообщения истории для показа пользователю (без разметки файлов)."""
        return self._files.to_plain_text(raw)
