"""Точка входа: python main.py"""

import asyncio
import logging
import sys

from bot.app import build_bot, build_container
from config.settings import ConfigError, Settings
from utils.logger import setup_logging

logger = logging.getLogger("main")


async def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings.logging.level, settings.logging.file)

    container = build_container(settings)
    await container.repository.init()
    bot = build_bot(container)

    logger.info(
        "Бот запускается: модель %s, резервные %s, хранилище %s",
        container.ai.model_name,
        ", ".join(container.ai.fallback_model_names) or "нет",
        settings.memory.users_dir,
    )
    try:
        await bot.run_polling()
    finally:
        await container.ai.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
