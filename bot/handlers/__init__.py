from vkbottle.bot import BotLabeler

from bot.container import Container
from bot.handlers import chat, dialogs, menu, modes, settings


def create_labelers(c: Container) -> list[BotLabeler]:
    """Порядок важен: команды → ожидание ввода (внутри dialogs, последним) → чат с моделью.

    Хендлеры блокирующие: первое совпадение останавливает обработку, поэтому
    «ловящий всё» чат-хендлер подключается строго последним.
    """
    return [
        menu.create_labeler(c),
        modes.create_labeler(c),
        settings.create_labeler(c),
        dialogs.create_labeler(c),
        chat.create_labeler(c),
    ]
