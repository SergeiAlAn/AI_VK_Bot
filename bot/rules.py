from collections.abc import Iterable
from typing import Any

from vkbottle.bot import Message
from vkbottle.dispatch.rules import ABCRule

from keyboards.payloads import Cmd
from models.user import PendingAction
from services.user_service import UserService


def _normalize(text: str | None) -> str:
    return " ".join((text or "").lower().split())


class CommandRule(ABCRule[Message]):
    """Срабатывает на кнопку с payload {"cmd": ...} или на текстовый синоним команды.

    В хендлер передаётся аргумент payload: dict (данные кнопки, например id диалога).
    """

    def __init__(self, *commands: Cmd, aliases: Iterable[str] = ()) -> None:
        self._commands = {c.value for c in commands}
        self._aliases = {_normalize(a) for a in aliases}

    async def check(self, event: Message) -> dict[str, Any] | bool:
        data = event.get_payload_json()
        if isinstance(data, dict):
            if data.get("cmd") in self._commands:
                return {"payload": data}
            # Стандартная кнопка «Начать» VK присылает {"command": "start"}
            if data.get("command") == "start" and Cmd.MENU.value in self._commands:
                return {"payload": {}}
            return False
        if _normalize(event.text) in self._aliases:
            return {"payload": {}}
        return False


class PendingActionRule(ABCRule[Message]):
    """Ловит обычный текст, если бот ждёт ввод для многошагового действия (например, нового названия)."""

    def __init__(self, users: UserService, action: PendingAction) -> None:
        self._users = users
        self._action = action

    async def check(self, event: Message) -> dict[str, Any] | bool:
        if event.payload:
            return False
        state = await self._users.get_state(event.from_id)
        if state.pending_action is self._action:
            return {"target_dialog_id": state.target_dialog_id}
        return False
