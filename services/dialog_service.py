import logging
from dataclasses import dataclass

from models.chat import Role
from models.dialog import Dialog
from models.mode import ChatMode
from models.user import UserProfile
from services.exceptions import DialogLimitError, DialogNotFoundError, InvalidDialogTitleError
from services.mode_registry import ModeRegistry
from services.user_service import UserService
from utils.text import truncate

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 40
AUTO_TITLE_LENGTH = 32


@dataclass(frozen=True, slots=True)
class DialogsOverview:
    dialogs: tuple[Dialog, ...]  # от последнего активного к самому старому
    active_dialog_id: str | None


@dataclass(frozen=True, slots=True)
class DeleteResult:
    deleted_title: str
    active_dialog: Dialog
    created_new: bool  # удалён последний диалог — создан новый пустой


class DialogService:
    """Менеджер диалогов: создание, список, переключение, переименование,
    удаление и смена режима общения активного диалога.

    Наружу отдаются копии моделей, чтобы случайное изменение объекта вне
    session() не приводило к рассинхронизации с файлом.
    """

    def __init__(self, users: UserService, modes: ModeRegistry, max_dialogs: int) -> None:
        self._users = users
        self._modes = modes
        self._max_dialogs = max_dialogs

    async def create(self, user_id: int, mode_id: str | None = None) -> Dialog:
        async with self._users.session(user_id) as profile:
            if len(profile.dialogs) >= self._max_dialogs:
                raise DialogLimitError(self._max_dialogs)
            mode = self._modes.resolve(mode_id or profile.settings.default_mode)
            profile.state.reset()
            dialog = UserService.add_dialog(profile, mode.id)
            logger.info("user=%s создал диалог %s (%s)", user_id, dialog.id, mode.id)
            return dialog.model_copy(deep=True)

    async def overview(self, user_id: int) -> DialogsOverview:
        profile = await self._users.get_profile(user_id)
        dialogs = sorted(profile.dialogs, key=lambda d: d.updated_at, reverse=True)
        return DialogsOverview(dialogs=tuple(dialogs), active_dialog_id=profile.active_dialog_id)

    async def get_active(self, user_id: int) -> Dialog:
        profile = await self._users.get_profile(user_id)
        dialog = profile.active_dialog
        assert dialog is not None  # гарантируется UserService._repair
        return dialog

    async def get(self, user_id: int, dialog_id: str) -> Dialog:
        profile = await self._users.get_profile(user_id)
        return _require(profile, dialog_id)

    async def switch(self, user_id: int, dialog_id: str) -> Dialog:
        """Переключает активный контекст: следующие сообщения пойдут в историю
        выбранного диалога и с его system prompt."""
        async with self._users.session(user_id) as profile:
            dialog = _require(profile, dialog_id)
            profile.active_dialog_id = dialog.id
            profile.state.reset()
            dialog.touch()
            logger.info("user=%s переключился на диалог %s", user_id, dialog.id)
            return dialog.model_copy(deep=True)

    async def rename(self, user_id: int, dialog_id: str, title: str) -> Dialog:
        title = " ".join(title.split())
        if not title or len(title) > MAX_TITLE_LENGTH:
            raise InvalidDialogTitleError(MAX_TITLE_LENGTH)

        async with self._users.session(user_id) as profile:
            dialog = _require(profile, dialog_id)
            dialog.title = title
            dialog.auto_title = False
            profile.state.reset()
            return dialog.model_copy(deep=True)

    async def delete(self, user_id: int, dialog_id: str) -> DeleteResult:
        async with self._users.session(user_id) as profile:
            dialog = _require(profile, dialog_id)
            profile.dialogs.remove(dialog)
            profile.state.reset()

            created_new = False
            if not profile.dialogs:
                active = UserService.add_dialog(profile, profile.settings.default_mode)
                created_new = True
            elif profile.active_dialog_id == dialog.id:
                active = max(profile.dialogs, key=lambda d: d.updated_at)
                profile.active_dialog_id = active.id
            else:
                active = profile.active_dialog  # type: ignore[assignment]

            logger.info("user=%s удалил диалог %s", user_id, dialog.id)
            return DeleteResult(
                deleted_title=dialog.title,
                active_dialog=active.model_copy(deep=True),
                created_new=created_new,
            )

    async def set_mode(self, user_id: int, mode_id: str) -> tuple[Dialog, ChatMode]:
        """Меняет режим только у активного диалога. История сохраняется, но со
        следующего сообщения модель получит новый system prompt.
        Выбранный режим также запоминается для новых диалогов."""
        mode = self._modes.get(mode_id)
        async with self._users.session(user_id) as profile:
            dialog = profile.active_dialog
            assert dialog is not None
            dialog.mode = mode.id
            dialog.touch()
            profile.settings.default_mode = mode.id
            logger.info("user=%s: диалог %s → режим %s", user_id, dialog.id, mode.id)
            return dialog.model_copy(deep=True), mode

    async def apply_auto_title(self, user_id: int, dialog_id: str, first_message: str) -> None:
        """Даёт диалогу название по первому сообщению, если пользователь не задал своё."""
        async with self._users.session(user_id) as profile:
            dialog = profile.find_dialog(dialog_id)
            if dialog is None or not dialog.auto_title:
                return
            user_messages = sum(1 for m in dialog.messages if m.role is Role.USER)
            if user_messages == 1:
                dialog.title = truncate(first_message, AUTO_TITLE_LENGTH)
            dialog.auto_title = False


def _require(profile: UserProfile, dialog_id: str) -> Dialog:
    dialog = profile.find_dialog(dialog_id)
    if dialog is None:
        raise DialogNotFoundError(dialog_id)
    return dialog
