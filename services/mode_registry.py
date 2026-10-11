from collections.abc import Iterable

from models.mode import ChatMode
from services.exceptions import UnknownModeError


class ModeRegistry:
    """Каталог режимов общения (ролей) с поиском по id."""

    def __init__(self, modes: Iterable[ChatMode], default_mode_id: str) -> None:
        self._modes: dict[str, ChatMode] = {mode.id: mode for mode in modes}
        if default_mode_id not in self._modes:
            raise ValueError(f"Режим по умолчанию {default_mode_id!r} не найден среди {list(self._modes)}")
        self._default_id = default_mode_id

    @property
    def default(self) -> ChatMode:
        return self._modes[self._default_id]

    def all(self) -> tuple[ChatMode, ...]:
        return tuple(self._modes.values())

    def get(self, mode_id: str) -> ChatMode:
        try:
            return self._modes[mode_id]
        except KeyError:
            raise UnknownModeError(mode_id) from None

    def resolve(self, mode_id: str | None) -> ChatMode:
        """Как get, но для неизвестного/удалённого режима возвращает режим по умолчанию."""
        return self._modes.get(mode_id or "", self.default)

    def exists(self, mode_id: str) -> bool:
        return mode_id in self._modes
