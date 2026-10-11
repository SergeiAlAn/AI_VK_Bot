"""Загрузка конфигурации приложения из переменных окружения / файла .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigError(RuntimeError):
    """Отсутствует или некорректна обязательная настройка."""


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Параметры конкретной LLM-модели.

    Вынесены отдельно, чтобы у основной и резервных моделей могли быть
    разные настройки (например, reasoning_effort поддерживают не все модели).
    """

    name: str
    max_completion_tokens: int | None = None
    reasoning_effort: str | None = None


@dataclass(frozen=True, slots=True)
class AISettings:
    api_key: str
    base_url: str
    primary_model: ModelConfig
    fallback_models: tuple[ModelConfig, ...] = ()
    timeout: float = 90.0
    max_retries: int = 2


@dataclass(frozen=True, slots=True)
class MemorySettings:
    users_dir: Path
    max_history_messages: int = 100
    max_context_chars: int = 60_000
    max_dialogs_per_user: int = 30
    default_mode: str = "assistant"


@dataclass(frozen=True, slots=True)
class MessageLimits:
    max_input_chars: int = 4000
    max_output_chunk_chars: int = 4000


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    level: str = "INFO"
    file: Path | None = None


@dataclass(frozen=True, slots=True)
class Settings:
    vk_group_token: str
    ai: AISettings
    memory: MemorySettings
    limits: MessageLimits = field(default_factory=MessageLimits)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Settings:
        load_dotenv(env_file or PROJECT_ROOT / ".env")

        max_tokens = _int("AI_MAX_COMPLETION_TOKENS", 8000)
        primary = ModelConfig(
            name=_str("AI_MODEL", "openai/gpt-5-mini"),
            max_completion_tokens=max_tokens,
            reasoning_effort=_str("AI_REASONING_EFFORT", "") or None,
        )
        fallbacks = tuple(
            ModelConfig(name=name, max_completion_tokens=max_tokens)
            for name in _list("AI_FALLBACK_MODELS")
            if name != primary.name
        )

        log_file = _str("LOG_FILE", "")
        return cls(
            vk_group_token=_required("VK_GROUP_TOKEN"),
            ai=AISettings(
                api_key=_required("PROXYAPI_KEY"),
                base_url=_str("PROXYAPI_BASE_URL", "https://api.proxyapi.ru/v1"),
                primary_model=primary,
                fallback_models=fallbacks,
                timeout=float(_str("AI_TIMEOUT", "90")),
                max_retries=_int("AI_MAX_RETRIES", 2),
            ),
            memory=MemorySettings(
                users_dir=_path(_str("USERS_DIR", "users")),
                max_history_messages=_int("MAX_HISTORY_MESSAGES", 100),
                max_context_chars=_int("MAX_CONTEXT_CHARS", 60_000),
                max_dialogs_per_user=_int("MAX_DIALOGS_PER_USER", 30),
                default_mode=_str("DEFAULT_MODE", "assistant"),
            ),
            limits=MessageLimits(
                max_input_chars=_int("MAX_INPUT_CHARS", 4000),
                # 4096 — жёсткий лимит VK на одно сообщение
                max_output_chunk_chars=min(_int("MAX_OUTPUT_CHUNK_CHARS", 4000), 4096),
            ),
            logging=LoggingSettings(
                level=_str("LOG_LEVEL", "INFO").upper(),
                file=_path(log_file) if log_file else None,
            ),
        )


def _str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Не задана обязательная переменная окружения {name} (см. .env.example)")
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должна быть целым числом, получено: {raw!r}") from exc


def _list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def _path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path
