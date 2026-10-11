import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from vkbottle import VKAPIError
from vkbottle.bot import Message

from bot import texts
from services.exceptions import DialogNotFoundError

logger = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[Any]]


def safe_handler(func: Handler) -> Handler:
    """Перехватывает ошибки внутри хендлера и отвечает пользователю.

    Важно делать это именно здесь: если исключение «улетит» в vkbottle, роутер
    передаст сообщение следующим хендлерам, и нажатие кнопки может попасть в
    чат с моделью. functools.wraps сохраняет сигнатуру для внедрения аргументов vkbottle.
    """

    @wraps(func)
    async def wrapper(message: Message, *args: Any, **kwargs: Any) -> None:
        try:
            await func(message, *args, **kwargs)
        except DialogNotFoundError:
            await _safe_answer(message, texts.DIALOG_NOT_FOUND)
        except VKAPIError[901, 902]:  # type: ignore[misc]
            logger.info("user=%s запретил сообщения от сообщества", message.from_id)
        except Exception:
            logger.exception("Ошибка в хендлере %s (user=%s)", func.__name__, message.from_id)
            await _safe_answer(message, texts.UNEXPECTED_ERROR)

    return wrapper


async def _safe_answer(message: Message, text: str) -> None:
    try:
        await message.answer(text)
    except Exception:
        logger.exception("Не удалось отправить сообщение об ошибке user=%s", message.from_id)
