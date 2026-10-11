"""Ошибки AI-слоя, не зависящие от конкретного SDK/провайдера.

retryable=True означает, что имеет смысл попробовать другую (резервную) модель.
"""


class AIError(Exception):
    retryable: bool = False

    def __init__(self, message: str = "", *, model: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.model = model


class AIAuthError(AIError):
    """401 — неверный ключ или base_url."""


class AIAccessDeniedError(AIError):
    """403 — модель/эндпоинт/IP не разрешены для ключа."""


class AIQuotaError(AIError):
    """402 — недостаточно средств или исчерпан бюджет ключа."""


class AIBadRequestError(AIError):
    """400/422 — некорректный запрос (в т.ч. переполнение контекста)."""


class AIModelNotFoundError(AIError):
    """404 — модель не найдена в каталоге."""

    retryable = True


class AIRateLimitError(AIError):
    """429 — превышен лимит частоты запросов."""

    retryable = True


class AIUnavailableError(AIError):
    """5xx — конечный сервис недоступен."""

    retryable = True


class AITimeoutError(AIUnavailableError):
    """Истекло время ожидания ответа."""


class AINetworkError(AIUnavailableError):
    """Сетевая ошибка: нет соединения, DNS, обрыв."""


class AIEmptyResponseError(AIError):
    """Модель вернула пустой ответ (например, весь лимит токенов ушёл на рассуждения)."""

    retryable = True
