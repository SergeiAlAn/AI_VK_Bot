import asyncio
import logging
import weakref
from pathlib import Path
from uuid import uuid4

import aiofiles
import aiofiles.os
from pydantic import ValidationError

from models.user import UserProfile
from storage.base import UserRepository
from utils.time import utc_now

logger = logging.getLogger(__name__)


class JsonUserRepository(UserRepository):
    """Хранит каждого пользователя в отдельном файле users/<user_id>.json.

    Гарантии:
    * асинхронный ввод-вывод (aiofiles), event loop не блокируется;
    * атомарная запись: сначала временный файл, затем os.replace — при падении
      процесса посреди записи старый файл остаётся целым;
    * повреждённый файл не роняет бота: он переименовывается в *.corrupted-*,
      а пользователь получает чистый профиль.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        # WeakValueDictionary: блокировка живёт, пока её кто-то держит или ждёт,
        # и не копится в памяти для тысяч неактивных пользователей
        self._locks: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()

    async def init(self) -> None:
        await aiofiles.os.makedirs(self._base_dir, exist_ok=True)

    def lock(self, user_id: int) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_id] = lock
        return lock

    def _path(self, user_id: int) -> Path:
        return self._base_dir / f"{int(user_id)}.json"

    async def get(self, user_id: int) -> UserProfile | None:
        path = self._path(user_id)
        if not await aiofiles.os.path.exists(path):
            return None

        async with aiofiles.open(path, encoding="utf-8") as file:
            raw = await file.read()

        try:
            return UserProfile.model_validate_json(raw)
        except ValidationError as exc:
            backup = path.with_name(f"{path.stem}.corrupted-{utc_now():%Y%m%d%H%M%S}.json")
            await aiofiles.os.replace(path, backup)
            logger.error(
                "Профиль %s повреждён (%d ошибок валидации), файл перемещён в %s",
                user_id,
                exc.error_count(),
                backup.name,
            )
            return None

    async def save(self, profile: UserProfile) -> None:
        profile.updated_at = utc_now()
        path = self._path(profile.user_id)
        tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        data = profile.model_dump_json(indent=2)

        try:
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as file:
                await file.write(data)
                await file.flush()
            await aiofiles.os.replace(tmp_path, path)
        except BaseException:
            if await aiofiles.os.path.exists(tmp_path):
                await aiofiles.os.remove(tmp_path)
            raise

    async def delete(self, user_id: int) -> None:
        path = self._path(user_id)
        if await aiofiles.os.path.exists(path):
            await aiofiles.os.remove(path)
