import logging
import time
from collections.abc import Sequence

from config.settings import ModelConfig
from models.chat import ChatMessage
from services.ai.base import AIProvider, AIRequest, AIResponse
from services.ai.context_builder import ContextBuilder
from services.ai.exceptions import AIError

logger = logging.getLogger(__name__)


class AIService:
    """Единая точка работы с LLM для всего приложения.

    * собирает контекст (system + история + сообщение пользователя);
    * вызывает провайдера с основной моделью;
    * при «временных» ошибках (429, 5xx, сеть, таймаут, пустой ответ, модель
      не найдена) переключается на резервные модели по очереди;
    * ошибки, которые резервная модель не исправит (ключ, баланс, доступ,
      некорректный запрос), пробрасывает сразу.

    Сменить модель — поменять AI_MODEL в .env; подключить другой API —
    передать другую реализацию AIProvider.
    """

    def __init__(
        self,
        provider: AIProvider,
        context_builder: ContextBuilder,
        primary_model: ModelConfig,
        fallback_models: Sequence[ModelConfig] = (),
    ) -> None:
        self._provider = provider
        self._context_builder = context_builder
        self._primary_model = primary_model
        self._fallback_models = tuple(fallback_models)

    @property
    def model_name(self) -> str:
        return self._primary_model.name

    @property
    def fallback_model_names(self) -> tuple[str, ...]:
        return tuple(m.name for m in self._fallback_models)

    async def generate_reply(
        self,
        system_prompt: str,
        history: Sequence[ChatMessage],
        user_message: str,
    ) -> AIResponse:
        messages = self._context_builder.build(system_prompt, history, user_message)
        last_error: AIError | None = None

        for model in (self._primary_model, *self._fallback_models):
            started = time.perf_counter()
            try:
                response = await self._provider.complete(AIRequest(model=model, messages=messages))
            except AIError as exc:
                last_error = exc
                logger.warning(
                    "Модель %s вернула ошибку %s: %s", model.name, type(exc).__name__, exc.message
                )
                if not exc.retryable:
                    raise
                continue

            logger.info(
                "Ответ от %s за %.1f c: context=%d сообщений, tokens in/out=%d/%d, finish=%s",
                response.model,
                time.perf_counter() - started,
                len(messages),
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.finish_reason,
            )
            return response

        assert last_error is not None
        raise last_error

    async def close(self) -> None:
        await self._provider.close()
