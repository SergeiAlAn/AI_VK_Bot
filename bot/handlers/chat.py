"""Общение с моделью: любой текст, не распознанный как команда, уходит в активный диалог."""

import logging

from vkbottle.bot import BotLabeler, Message

from bot import texts
from bot.container import Container
from bot.errors import safe_handler
from bot.sender import send_files, send_long
from bot.thinking import ThinkingIndicator
from services.ai import AIError
from services.exceptions import EmptyMessageError, MessageTooLongError, UserBusyError

logger = logging.getLogger(__name__)


def create_labeler(c: Container) -> BotLabeler:
    labeler = BotLabeler()
    chunk_limit = c.settings.limits.max_output_chunk_chars
    # VK держит постоянную клавиатуру, пока бот не пришлёт новую. Прикрепляем меню
    # ко всем ответам этого хендлера, чтобы у пользователя всегда были актуальные кнопки
    menu = c.keyboards.main_menu

    @labeler.private_message()
    @safe_handler
    async def chat(message: Message) -> None:
        user_id = message.from_id

        if message.payload:
            # Ни одна команда не распознала payload — это кнопка от старой клавиатуры
            # (в т.ч. от прошлых версий бота). Не отправляем её подпись в модель
            logger.info("user=%s нажал устаревшую кнопку: %s", user_id, message.payload)
            await message.answer(texts.OLD_KEYBOARD, keyboard=menu)
            return

        # Валидация до индикатора «думаю», чтобы не дёргать API впустую
        try:
            c.chat.validate(message.text)
        except EmptyMessageError:
            await message.answer(
                texts.NON_TEXT_MESSAGE if message.attachments else texts.EMPTY_MESSAGE, keyboard=menu
            )
            return
        except MessageTooLongError as exc:
            await message.answer(texts.TOO_LONG.format(length=exc.length, limit=exc.limit), keyboard=menu)
            return

        if c.chat.is_busy(user_id):
            await message.answer(texts.BUSY)
            return

        try:
            async with ThinkingIndicator(message.ctx_api, message.peer_id, texts.THINKING):
                reply = await c.chat.ask(user_id, message.text)
        except UserBusyError:
            await message.answer(texts.BUSY)
            return
        except AIError as exc:
            # Fallback: пользователь получает понятное сообщение, история не портится
            logger.error("AI недоступен для user=%s: %s (%s)", user_id, type(exc).__name__, exc.message)
            await message.answer(texts.ai_error(exc), keyboard=menu)
            return

        text = reply.text or (texts.FILES_READY if reply.files else "")
        active = await c.dialogs.get_active(user_id)
        if active.id != reply.dialog.id:
            # Пользователь переключил диалог, пока модель думала
            text = texts.ANSWER_IN_OTHER_DIALOG.format(title=reply.dialog.title) + text
        if reply.truncated:
            text += texts.TRUNCATED_NOTE

        await send_long(message, text, chunk_limit, keyboard=None if reply.files else menu)
        if reply.files:
            await send_files(message, reply.files, chunk_limit, keyboard=menu)

    return labeler
