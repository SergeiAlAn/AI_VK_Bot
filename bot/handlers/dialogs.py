"""Многодиалоговый режим: создание, список, переключение, переименование, удаление."""

from typing import Any

from vkbottle.bot import BotLabeler, Message

from bot import texts
from bot.container import Container
from bot.errors import safe_handler
from bot.rules import CommandRule, PendingActionRule
from keyboards import Buttons, Cmd
from models.user import PendingAction
from services.dialog_service import MAX_TITLE_LENGTH
from services.exceptions import DialogLimitError, DialogNotFoundError, InvalidDialogTitleError


def create_labeler(c: Container) -> BotLabeler:
    labeler = BotLabeler()
    modes_by_id = {m.id: m for m in c.modes.all()}

    async def show_dialogs(message: Message, page: int = 0) -> None:
        overview = await c.dialogs.overview(message.from_id)
        pages = c.keyboards.page_count(len(overview.dialogs))
        await message.answer(
            texts.dialogs_list(
                overview.dialogs,
                overview.active_dialog_id,
                modes_by_id,
                page=page,
                page_size=c.keyboards.dialogs_page_size,
                pages=pages,
                limit=c.settings.memory.max_dialogs_per_user,
            ),
            keyboard=c.keyboards.dialogs_list(overview.dialogs, overview.active_dialog_id, page),
        )

    @labeler.private_message(CommandRule(Cmd.NEW_DIALOG, aliases=(Buttons.NEW_DIALOG, "новый диалог", "/new")))
    @safe_handler
    async def new_dialog(message: Message) -> None:
        try:
            dialog = await c.dialogs.create(message.from_id)
        except DialogLimitError as exc:
            await message.answer(texts.DIALOG_LIMIT.format(limit=exc.limit))
            return
        mode = c.modes.resolve(dialog.mode)
        await message.answer(
            texts.DIALOG_CREATED.format(title=dialog.title, mode=mode.label),
            keyboard=c.keyboards.main_menu,
        )

    @labeler.private_message(CommandRule(Cmd.DIALOGS, aliases=(Buttons.DIALOGS, "список диалогов", "мои диалоги", "диалоги", "/dialogs")))
    @safe_handler
    async def list_dialogs(message: Message, payload: dict[str, Any]) -> None:
        await show_dialogs(message, page=int(payload.get("page", 0)))

    @labeler.private_message(CommandRule(Cmd.SWITCH_DIALOG))
    @safe_handler
    async def switch_dialog(message: Message, payload: dict[str, Any]) -> None:
        dialog = await c.dialogs.switch(message.from_id, str(payload["id"]))
        await message.answer(
            texts.switched(dialog, c.modes.resolve(dialog.mode), c.chat.preview),
            keyboard=c.keyboards.main_menu,
        )

    @labeler.private_message(CommandRule(Cmd.DELETE_DIALOG))
    @safe_handler
    async def ask_delete(message: Message, payload: dict[str, Any]) -> None:
        dialog = await c.dialogs.get(message.from_id, str(payload["id"]))
        await message.answer(
            texts.CONFIRM_DELETE.format(title=dialog.title, count=len(dialog.messages)),
            keyboard=c.keyboards.confirm_delete(dialog.id),
        )

    @labeler.private_message(CommandRule(Cmd.CONFIRM_DELETE))
    @safe_handler
    async def confirm_delete(message: Message, payload: dict[str, Any]) -> None:
        result = await c.dialogs.delete(message.from_id, str(payload["id"]))
        await message.answer(
            texts.dialog_deleted(result.deleted_title, result.active_dialog, result.created_new),
            keyboard=c.keyboards.main_menu,
        )
        await show_dialogs(message)

    @labeler.private_message(CommandRule(Cmd.RENAME_DIALOG, aliases=("переименовать",)))
    @safe_handler
    async def ask_rename(message: Message) -> None:
        dialog = await c.dialogs.get_active(message.from_id)
        await c.users.set_pending_action(message.from_id, PendingAction.RENAME_DIALOG, dialog.id)
        await message.answer(
            texts.RENAME_PROMPT.format(title=dialog.title, limit=MAX_TITLE_LENGTH),
            keyboard=c.keyboards.cancel,
        )

    @labeler.private_message(PendingActionRule(c.users, PendingAction.RENAME_DIALOG))
    @safe_handler
    async def rename_input(message: Message, target_dialog_id: str | None) -> None:
        if target_dialog_id is None:
            await c.users.clear_pending_action(message.from_id)
            return
        try:
            dialog = await c.dialogs.rename(message.from_id, target_dialog_id, message.text)
        except InvalidDialogTitleError as exc:
            await message.answer(texts.RENAME_INVALID.format(limit=exc.max_length), keyboard=c.keyboards.cancel)
            return
        except DialogNotFoundError:
            await c.users.clear_pending_action(message.from_id)
            raise
        await message.answer(texts.RENAMED.format(title=dialog.title), keyboard=c.keyboards.main_menu)

    return labeler
