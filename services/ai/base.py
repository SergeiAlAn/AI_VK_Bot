from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from config.settings import ModelConfig

ContextRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class ContextMessage:
    role: ContextRole
    content: str


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class AIRequest:
    model: ModelConfig
    messages: tuple[ContextMessage, ...]


@dataclass(frozen=True, slots=True)
class AIResponse:
    content: str
    model: str
    finish_reason: str | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)

    @property
    def truncated(self) -> bool:
        """Ответ оборван из-за лимита max_completion_tokens."""
        return self.finish_reason == "length"


class AIProvider(ABC):
    """Интерфейс провайдера LLM.

    Чтобы подключить другой API (например, нативный Anthropic Messages или
    локальную модель), достаточно реализовать этот класс — AIService и бот
    останутся без изменений.
    """

    name: str = "provider"

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse:
        """Выполняет запрос. Должен бросать только исключения из services.ai.exceptions."""

    async def close(self) -> None:  # noqa: B027 — необязательный хук
        """Освобождает ресурсы (HTTP-сессии и т.п.)."""
