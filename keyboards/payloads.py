from enum import StrEnum
from typing import Any


class Cmd(StrEnum):
    """Команды, которые передаются в payload кнопок: {"cmd": "...", ...}."""

    MENU = "menu"
    HELP = "help"
    NEW_DIALOG = "new_dialog"
    DIALOGS = "dialogs"
    SWITCH_DIALOG = "switch_dialog"
    DELETE_DIALOG = "delete_dialog"
    CONFIRM_DELETE = "confirm_delete"
    RENAME_DIALOG = "rename_dialog"
    SETTINGS = "settings"
    MODES = "modes"
    SET_MODE = "set_mode"
    MODEL_INFO = "model_info"
    CLEAR_HISTORY = "clear_history"
    CONFIRM_CLEAR = "confirm_clear"
    CANCEL = "cancel"


def payload(cmd: Cmd, **data: Any) -> dict[str, Any]:
    # VK ограничивает payload 255 байтами — передаём только короткие id
    return {"cmd": cmd.value, **data}
