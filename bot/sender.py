import asyncio
import logging
from collections.abc import Sequence

from vkbottle import DocMessagesUploader
from vkbottle.bot import Message

from bot import texts
from services.files import GeneratedFile
from utils.text import split_text

logger = logging.getLogger(__name__)

UPLOAD_ATTEMPTS = 3
UPLOAD_RETRY_DELAY = 1.5  # секунды; растёт линейно: 1.5, 3.0


async def send_long(message: Message, text: str, chunk_limit: int, keyboard: str | None = None) -> None:
    """Отправляет текст любой длины несколькими сообщениями, разрезая по абзацам.

    Клавиатура прикрепляется к последней части, чтобы кнопки были под концом ответа.
    """
    chunks = split_text(text, chunk_limit) or [text]
    for index, chunk in enumerate(chunks):
        is_last = index == len(chunks) - 1
        await message.answer(chunk, keyboard=keyboard if is_last else None, dont_parse_links=True)


async def send_files(
    message: Message,
    files: Sequence[GeneratedFile],
    chunk_limit: int,
    keyboard: str | None = None,
) -> None:
    """Загружает файлы как документы VK и отправляет их в чат.

    Если загрузка не удалась и после повторов, содержимое файла отправляется
    обычным текстом — пользователь не теряет результат.
    """
    uploader = DocMessagesUploader(message.ctx_api)
    for index, file in enumerate(files):
        is_last = index == len(files) - 1
        attachment = await _upload_with_retries(uploader, file, message)
        if attachment is None:
            await send_long(
                message,
                texts.FILE_UPLOAD_FAILED.format(name=file.name) + file.content,
                chunk_limit,
                keyboard=keyboard if is_last else None,
            )
            continue
        await message.answer(
            texts.FILE_CAPTION.format(name=file.name),
            attachment=attachment,
            keyboard=keyboard if is_last else None,
        )


async def _upload_with_retries(
    uploader: DocMessagesUploader, file: GeneratedFile, message: Message
) -> str | None:
    """Сервер загрузки VK периодически отвечает «not saved» или пустым телом на
    корректный файл, а через пару секунд принимает его. Каждая попытка берёт
    новый upload_url, поэтому повтор действительно помогает."""
    for attempt in range(1, UPLOAD_ATTEMPTS + 1):
        try:
            return await uploader.upload(file.to_bytes(), peer_id=message.peer_id, title=file.name)
        except Exception as exc:
            logger.warning(
                "Загрузка файла %s для user=%s, попытка %d/%d: %s",
                file.name, message.from_id, attempt, UPLOAD_ATTEMPTS, exc,
            )
            if attempt < UPLOAD_ATTEMPTS:
                await asyncio.sleep(UPLOAD_RETRY_DELAY * attempt)
    return None
