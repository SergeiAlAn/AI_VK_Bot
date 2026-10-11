"""Смена режима общения (роли) для текущего диалога."""

from typing import Any

from vkbottle.bot import BotLabeler, Message

from bot import texts
from bot.container import Container
from bot.errors import safe_handler
from bot.rules import CommandRule
from keyboards import Buttons, Cmd
from services.exceptions import UnknownModeError


def create_labeler(c: Container) -> BotLabeler:
    labeler = BotLabeler()

    @labeler.private_message(CommandRule(Cmd.MODES, aliases=(Buttons.MODES, "сменить режим", "режим", "/mode")))
    @safe_handler
    async def show_modes(message: Message) -> None:
        dialog = await c.dialogs.get_active(message.from_id)
        current = c.modes.resolve(dialog.mode)
        await message.answer(
            texts.modes_list(c.modes.all(), current, dialog),
            keyboard=c.keyboards.modes(c.modes.all(), current.id),
        )

    @labeler.private_message(CommandRule(Cmd.SET_MODE))
    @safe_handler
    async def set_mode(message: Message, payload: dict[str, Any]) -> None:
        try:
            dialog, mode = await c.dialogs.set_mode(message.from_id, str(payload.get("mode")))
        except UnknownModeError:
            await show_modes(message)
            return
        await message.answer(
            texts.MODE_CHANGED.format(title=dialog.title, mode=mode.label, description=mode.description),
            keyboard=c.keyboards.main_menu,
        )

    return labeler
