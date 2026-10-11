import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Единая настройка логирования: консоль + (опционально) файл с ротацией."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        )

    logging.basicConfig(level=level, format=_FORMAT, handlers=handlers, force=True)

    # Сторонние библиотеки слишком многословны на DEBUG/INFO
    for noisy in ("httpx", "httpx2", "httpcore", "httpcore2", "openai", "aiohttp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.getLogger("vkbottle").setLevel(logging.INFO if level == "DEBUG" else logging.WARNING)
