from typing import Any

from vkbottle.bot import BotLabeler, Message

from bot import texts
from bot.container import Container
from bot.errors import safe_handler
from bot.rules import CommandRule
from keyboards import Buttons, Cmd


def create_labeler(c: Container) -> BotLabeler:
    labeler = BotLabeler()

    @labeler.private_message(CommandRule(Cmd.MENU, aliases=("начать", "старт", "start", "/start", "меню", "/menu", "главное меню")))
    @safe_handler
    async def start(message: Message) -> None:
        # Первое обращение автоматически создаёт JSON-профиль пользователя
        profile = await c.users.get_profile(message.from_id)
        is_new = len(profile.dialogs) == 1 and not profile.dialogs[0].messages
        await message.answer(texts.WELCOME if is_new else texts.MENU, keyboard=c.keyboards.main_menu)

    @labeler.private_message(CommandRule(Cmd.HELP, aliases=(Buttons.HELP, "помощь", "/help", "help")))
    @safe_handler
    async def help_(message: Message) -> None:
        await message.answer(
            texts.help_text(c.modes.all(), c.memory.max_history),
            keyboard=c.keyboards.main_menu,
        )

    @labeler.private_message(CommandRule(Cmd.CANCEL, aliases=("отмена", "/cancel")))
    @safe_handler
    async def cancel(message: Message, payload: dict[str, Any]) -> None:
        await c.users.clear_pending_action(message.from_id)
        await message.answer(texts.CANCELLED, keyboard=c.keyboards.main_menu)

    return labeler
