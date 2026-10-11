from collections.abc import Sequence

from models.chat import ChatMessage, Role
from services.ai.base import ContextMessage


class ContextBuilder:
    """Формирует context window для модели.

    Итоговый порядок: [system] + последние N сообщений истории (user/assistant)
    + новое сообщение пользователя. Дополнительно соблюдается бюджет по символам,
    чтобы длинная история не переполнила контекстное окно модели: при превышении
    отбрасываются самые старые сообщения.
    """

    def __init__(self, max_messages: int = 100, max_chars: int = 60_000) -> None:
        self._max_messages = max_messages
        self._max_chars = max_chars

    def build(
        self,
        system_prompt: str,
        history: Sequence[ChatMessage],
        user_message: str,
    ) -> tuple[ContextMessage, ...]:
        budget = self._max_chars - len(system_prompt) - len(user_message)

        selected: list[ContextMessage] = []
        # Идём с конца, чтобы при нехватке бюджета терять самые старые сообщения
        for message in reversed(history[-self._max_messages :]):
            if message.role is Role.SYSTEM or not message.content:
                continue
            budget -= len(message.content)
            if budget < 0:
                break
            selected.append(ContextMessage(role=message.role.value, content=message.content))
        selected.reverse()

        # Контекст не должен начинаться с ответа ассистента без вопроса
        while selected and selected[0].role == "assistant":
            selected.pop(0)

        return (
            ContextMessage(role="system", content=system_prompt),
            *selected,
            ContextMessage(role="user", content=user_message),
        )
