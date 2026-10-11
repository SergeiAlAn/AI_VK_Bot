"""Сборка приложения (composition root): здесь и только здесь создаются все зависимости."""

from vkbottle import API
from vkbottle.bot import Bot, BotLabeler

from bot.container import Container
from bot.handlers import create_labelers
from bot.middlewares import LoggingMiddleware, OnlyUsersMiddleware, build_pending_reset_middleware
from config.prompts import CHAT_MODES
from config.settings import Settings
from keyboards.factory import KeyboardFactory
from services.ai.ai_service import AIService
from services.ai.context_builder import ContextBuilder
from services.ai.openai_provider import OpenAICompatibleProvider
from services.chat_service import ChatService
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from services.mode_registry import ModeRegistry
from services.user_service import UserService
from storage.json_repository import JsonUserRepository


def build_container(settings: Settings) -> Container:
    modes = ModeRegistry(CHAT_MODES, settings.memory.default_mode)
    repository = JsonUserRepository(settings.memory.users_dir)
    users = UserService(repository, modes)
    dialogs = DialogService(users, modes, settings.memory.max_dialogs_per_user)
    memory = MemoryService(users, settings.memory.max_history_messages)

    provider = OpenAICompatibleProvider(
        api_key=settings.ai.api_key,
        base_url=settings.ai.base_url,
        timeout=settings.ai.timeout,
        max_retries=settings.ai.max_retries,
    )
    ai = AIService(
        provider=provider,
        context_builder=ContextBuilder(
            max_messages=settings.memory.max_history_messages,
            max_chars=settings.memory.max_context_chars,
        ),
        primary_model=settings.ai.primary_model,
        fallback_models=settings.ai.fallback_models,
    )
    chat = ChatService(ai, dialogs, memory, modes, settings.limits.max_input_chars)

    return Container(
        settings=settings,
        repository=repository,
        modes=modes,
        users=users,
        dialogs=dialogs,
        memory=memory,
        ai=ai,
        chat=chat,
        keyboards=KeyboardFactory(),
    )


def build_bot(container: Container) -> Bot:
    labeler = BotLabeler()
    labeler.message_view.register_middleware(OnlyUsersMiddleware)
    labeler.message_view.register_middleware(build_pending_reset_middleware(container.users))
    labeler.message_view.register_middleware(LoggingMiddleware)

    for child in create_labelers(container):
        labeler.load(child)

    return Bot(api=API(container.settings.vk_group_token), labeler=labeler)
