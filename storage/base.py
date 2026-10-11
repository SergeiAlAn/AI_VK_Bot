import asyncio
from abc import ABC, abstractmethod

from models.user import UserProfile


class UserRepository(ABC):
    """Абстракция хранилища профилей.

    Сервисы зависят только от этого интерфейса, поэтому JSON-хранилище можно
    заменить (например, на Redis или S3) без изменений бизнес-логики.
    """

    @abstractmethod
    async def get(self, user_id: int) -> UserProfile | None: ...

    @abstractmethod
    async def save(self, profile: UserProfile) -> None: ...

    @abstractmethod
    async def delete(self, user_id: int) -> None: ...

    @abstractmethod
    def lock(self, user_id: int) -> asyncio.Lock:
        """Блокировка на пользователя для атомарного цикла «прочитать → изменить → записать»."""
