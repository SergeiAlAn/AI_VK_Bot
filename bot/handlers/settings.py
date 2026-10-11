"""Настройки: информация о модели и очистка истории текущего диалога."""

from vkbottle.bot import BotLabeler, Message

from bot import texts
from bot.container import Container
from bot.errors import safe_handler
from bot.rules import CommandRule
from keyboards import Buttons, Cmd


def create_labeler(c: Container) -> BotLabeler:
    labeler = BotLabeler()

    @labeler.private_message(CommandRule(Cmd.SETTINGS, aliases=(Buttons.SETTINGS, "настройки", "/settings")))
    @safe_handler
    async def show_settings(message: Message) -> None:
        profile = await c.users.get_profile(message.from_id)
        dialog = profile.active_dialog
        assert dialog is not None
        await message.answer(
            texts.settings(
                dialog,
                c.modes.resolve(dialog.mode),
                c.ai.model_name,
                c.memory.max_history,
                len(profile.dialogs),
            ),
            keyboard=c.keyboards.settings,
        )

    @labeler.private_message(CommandRule(Cmd.MODEL_INFO, aliases=("модель", "/model")))
    @safe_handler
    async def model_info(message: Message) -> None:
        await message.answer(
            texts.model_info(c.ai.model_name, c.ai.fallback_model_names, c.memory.max_history)
        )

    @labeler.private_message(CommandRule(Cmd.CLEAR_HISTORY, aliases=("очистить историю", "/clear")))
    @safe_handler
    async def ask_clear(message: Message) -> None:
        dialog = await c.dialogs.get_active(message.from_id)
        if not dialog.messages:
            await message.answer(texts.HISTORY_ALREADY_EMPTY.format(title=dialog.title))
            return
        await message.answer(
            texts.CONFIRM_CLEAR.format(title=dialog.title, count=len(dialog.messages)),
            keyboard=c.keyboards.confirm_clear,
        )

    @labeler.private_message(CommandRule(Cmd.CONFIRM_CLEAR))
    @safe_handler
    async def confirm_clear(message: Message) -> None:
        dialog = await c.dialogs.get_active(message.from_id)
        removed = await c.memory.clear(message.from_id, dialog.id)
        await message.answer(
            texts.HISTORY_CLEARED.format(title=dialog.title, count=removed),
            keyboard=c.keyboards.main_menu,
        )

    return labeler
