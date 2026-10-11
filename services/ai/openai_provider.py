import logging
from typing import Any

import openai
from openai import AsyncOpenAI

from services.ai.base import AIProvider, AIRequest, AIResponse, TokenUsage
from services.ai.exceptions import (
    AIAccessDeniedError,
    AIAuthError,
    AIBadRequestError,
    AIEmptyResponseError,
    AIError,
    AIModelNotFoundError,
    AINetworkError,
    AIQuotaError,
    AIRateLimitError,
    AITimeoutError,
    AIUnavailableError,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(AIProvider):
    """Провайдер для любого OpenAI-совместимого Chat Completions API.

    Используется с ProxyAPI: base_url=https://api.proxyapi.ru/v1, а модель
    указывается полным идентификатором «вендор/модель» (openai/gpt-5-mini,
    anthropic/claude-haiku-4-5, google/gemini-2.5-flash ...). Поэтому через
    один провайдер доступны модели разных вендоров.
    """

    name = "proxyapi"

    def __init__(self, api_key: str, base_url: str, timeout: float, max_retries: int) -> None:
        # max_retries: SDK сам повторяет 408/409/429/5xx и сетевые сбои с экспоненциальной задержкой
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def complete(self, request: AIRequest) -> AIResponse:
        model = request.model
        params: dict[str, Any] = {
            "model": model.name,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        # gpt-5-* — reasoning-модели: вместо max_tokens используется max_completion_tokens,
        # а temperature не поддерживается (только значение по умолчанию)
        if model.max_completion_tokens:
            params["max_completion_tokens"] = model.max_completion_tokens
        if model.reasoning_effort:
            params["reasoning_effort"] = model.reasoning_effort

        try:
            completion = await self._client.chat.completions.create(**params)
        except openai.OpenAIError as exc:
            raise _map_error(exc, model.name) from exc

        if not completion.choices:
            raise AIEmptyResponseError("Ответ без choices", model=model.name)

        choice = completion.choices[0]
        content = (choice.message.content or "").strip()
        if not content:
            raise AIEmptyResponseError(
                f"Пустой ответ модели (finish_reason={choice.finish_reason})", model=model.name
            )

        usage = completion.usage
        return AIResponse(
            content=content,
            model=completion.model or model.name,
            finish_reason=choice.finish_reason,
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
        )

    async def close(self) -> None:
        await self._client.close()


def _map_error(exc: openai.OpenAIError, model: str) -> AIError:
    """Переводит исключения OpenAI SDK в доменные ошибки AI-слоя."""
    # APITimeoutError — подкласс APIConnectionError, поэтому проверяется первым
    if isinstance(exc, openai.APITimeoutError):
        return AITimeoutError("Превышено время ожидания ответа", model=model)
    if isinstance(exc, openai.APIConnectionError):
        return AINetworkError(f"Сетевая ошибка: {exc}", model=model)
    if not isinstance(exc, openai.APIStatusError):
        return AIError(str(exc), model=model)

    message = _extract_message(exc)
    status = exc.status_code
    error_cls: type[AIError]
    match status:
        case 401:
            error_cls = AIAuthError
        case 402:
            error_cls = AIQuotaError
        case 403:
            error_cls = AIAccessDeniedError
        case 404:
            error_cls = AIModelNotFoundError
        case 429:
            error_cls = AIRateLimitError
        case 400 | 422:
            error_cls = AIBadRequestError
        case _ if status >= 500:
            error_cls = AIUnavailableError
        case _:
            error_cls = AIError
    return error_cls(f"HTTP {status}: {message}", model=model)


def _extract_message(exc: openai.APIStatusError) -> str:
    """ProxyAPI отвечает {"detail": ...} на свои проверки и {"error": {...}} на ошибки вендора."""
    body = exc.body
    if isinstance(body, dict):
        if isinstance(body.get("detail"), str):
            return body["detail"]
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(body.get("message"), str):
            return body["message"]
    return exc.message
