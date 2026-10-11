import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from models.dialog import Dialog
from models.user import PendingAction, UserProfile, UserSettings, UserState
from services.mode_registry import ModeRegistry
from storage.base import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Управляет жизненным циклом профиля пользователя.

    Профиль (JSON-файл) создаётся автоматически при первом обращении.
    Все изменения выполняются через session(): чтение и запись происходят
    под блокировкой пользователя, поэтому параллельные события одного
    пользователя не перетирают изменения друг друга.
    """

    def __init__(self, repository: UserRepository, modes: ModeRegistry) -> None:
        self._repository = repository
        self._modes = modes

    @asynccontextmanager
    async def session(self, user_id: int) -> AsyncIterator[UserProfile]:
        """Транзакция над профилем: изменения сохраняются, только если блок завершился без ошибки."""
        async with self._repository.lock(user_id):
            profile = await self._load_or_create(user_id)
            yield profile
            await self._repository.save(profile)

    async def get_profile(self, user_id: int) -> UserProfile:
        """Снимок профиля только для чтения (изменения в нём не сохраняются)."""
        async with self._repository.lock(user_id):
            profile = await self._load_or_create(user_id)
        return profile

    async def get_state(self, user_id: int) -> UserState:
        return (await self.get_profile(user_id)).state

    async def set_pending_action(
        self, user_id: int, action: PendingAction, target_dialog_id: str | None = None
    ) -> None:
        async with self.session(user_id) as profile:
            profile.state.pending_action = action
            profile.state.target_dialog_id = target_dialog_id

    async def clear_pending_action(self, user_id: int) -> None:
        async with self.session(user_id) as profile:
            profile.state.reset()

    @staticmethod
    def add_dialog(profile: UserProfile, mode_id: str) -> Dialog:
        """Создаёт диалог внутри профиля и делает его активным (вызывать внутри session)."""
        profile.dialogs_created += 1
        dialog = Dialog(title=f"Диалог №{profile.dialogs_created}", mode=mode_id)
        profile.dialogs.append(dialog)
        profile.active_dialog_id = dialog.id
        return dialog

    async def _load_or_create(self, user_id: int) -> UserProfile:
        profile = await self._repository.get(user_id)
        if profile is None:
            profile = UserProfile(
                user_id=user_id,
                settings=UserSettings(default_mode=self._modes.default.id),
            )
            self.add_dialog(profile, profile.settings.default_mode)
            await self._repository.save(profile)
            logger.info("Создан профиль пользователя %s", user_id)
            return profile

        if self._repair(profile):
            await self._repository.save(profile)
        return profile

    def _repair(self, profile: UserProfile) -> bool:
        """Восстанавливает инварианты профиля (например, после ручной правки JSON
        или удаления режима из конфигурации). Возвращает True, если были изменения."""
        changed = False

        if not self._modes.exists(profile.settings.default_mode):
            profile.settings.default_mode = self._modes.default.id
            changed = True

        for dialog in profile.dialogs:
            if not self._modes.exists(dialog.mode):
                dialog.mode = profile.settings.default_mode
                changed = True

        if not profile.dialogs:
            self.add_dialog(profile, profile.settings.default_mode)
            changed = True
        elif profile.active_dialog is None:
            profile.active_dialog_id = max(profile.dialogs, key=lambda d: d.updated_at).id
            changed = True

        return changed
