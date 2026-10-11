from collections.abc import Sequence
from functools import cached_property

from vkbottle import Keyboard, KeyboardButtonColor, Text

from keyboards.payloads import Cmd, payload
from models.dialog import Dialog
from models.mode import ChatMode
from utils.text import truncate

# Лимиты VK: длина подписи кнопки — 40 символов; inline-клавиатура — до 10 кнопок и до 6 рядов
LABEL_LIMIT = 40
INLINE_BUTTONS_LIMIT = 10
MODES_PER_ROW = 2  # 10 режимов по 2 в ряд = 5 рядов, укладываемся в лимит 6


class Buttons:
    """Подписи кнопок главного меню (используются и для распознавания ввода текстом)."""

    NEW_DIALOG = "🆕 Новый диалог"
    DIALOGS = "📂 Список диалогов"
    MODES = "🎭 Сменить режим"
    SETTINGS = "⚙️ Настройки"
    HELP = "❓ Помощь"


class KeyboardFactory:
    """Строит все клавиатуры бота. Возвращает готовый JSON для messages.send."""

    def __init__(self, dialogs_page_size: int = 3) -> None:
        # Строка списка = 2 кнопки (открыть + удалить), плюс до 2 кнопок навигации
        # и 2 кнопки действий («Новый», «Переименовать»)
        if dialogs_page_size * 2 + 4 > INLINE_BUTTONS_LIMIT:
            raise ValueError("dialogs_page_size слишком большой для inline-клавиатуры VK")
        self.dialogs_page_size = dialogs_page_size

    @cached_property
    def main_menu(self) -> str:
        """Постоянная клавиатура под полем ввода. Статична, поэтому JSON строится один раз."""
        return (
            Keyboard(one_time=False)
            .add(Text(Buttons.NEW_DIALOG, payload(Cmd.NEW_DIALOG)), KeyboardButtonColor.POSITIVE)
            .add(Text(Buttons.DIALOGS, payload(Cmd.DIALOGS)), KeyboardButtonColor.PRIMARY)
            .row()
            .add(Text(Buttons.MODES, payload(Cmd.MODES)), KeyboardButtonColor.SECONDARY)
            .add(Text(Buttons.SETTINGS, payload(Cmd.SETTINGS)), KeyboardButtonColor.SECONDARY)
            .row()
            .add(Text(Buttons.HELP, payload(Cmd.HELP)), KeyboardButtonColor.SECONDARY)
            .get_json()
        )

    def page_count(self, total: int) -> int:
        return max(1, -(-total // self.dialogs_page_size))

    def dialogs_list(self, dialogs: Sequence[Dialog], active_id: str | None, page: int) -> str:
        page = min(max(page, 0), self.page_count(len(dialogs)) - 1)
        start = page * self.dialogs_page_size
        keyboard = Keyboard(inline=True)

        for index, dialog in enumerate(dialogs[start : start + self.dialogs_page_size]):
            if index:
                keyboard.row()
            is_active = dialog.id == active_id
            mark = "✅" if is_active else "💬"
            keyboard.add(
                Text(_label(f"{mark} {dialog.title}"), payload(Cmd.SWITCH_DIALOG, id=dialog.id)),
                KeyboardButtonColor.POSITIVE if is_active else KeyboardButtonColor.SECONDARY,
            )
            keyboard.add(
                Text("🗑", payload(Cmd.DELETE_DIALOG, id=dialog.id)), KeyboardButtonColor.NEGATIVE
            )

        has_prev = page > 0
        has_next = start + self.dialogs_page_size < len(dialogs)
        if has_prev or has_next:
            keyboard.row()
            if has_prev:
                keyboard.add(Text("⬅️ Назад", payload(Cmd.DIALOGS, page=page - 1)))
            if has_next:
                keyboard.add(Text("Далее ➡️", payload(Cmd.DIALOGS, page=page + 1)))

        keyboard.row()
        keyboard.add(Text("🆕 Новый", payload(Cmd.NEW_DIALOG)), KeyboardButtonColor.POSITIVE)
        keyboard.add(Text("✏️ Переименовать текущий", payload(Cmd.RENAME_DIALOG)), KeyboardButtonColor.PRIMARY)
        return keyboard.get_json()

    def confirm_delete(self, dialog_id: str) -> str:
        return (
            Keyboard(inline=True)
            .add(Text("🗑 Да, удалить", payload(Cmd.CONFIRM_DELETE, id=dialog_id)), KeyboardButtonColor.NEGATIVE)
            .add(Text("↩️ Отмена", payload(Cmd.DIALOGS)), KeyboardButtonColor.SECONDARY)
            .get_json()
        )

    def modes(self, modes: Sequence[ChatMode], current_mode_id: str) -> str:
        if len(modes) > INLINE_BUTTONS_LIMIT:
            raise ValueError(f"Inline-клавиатура VK вмещает не более {INLINE_BUTTONS_LIMIT} режимов")
        keyboard = Keyboard(inline=True)
        for index, mode in enumerate(modes):
            if index and index % MODES_PER_ROW == 0:
                keyboard.row()
            is_current = mode.id == current_mode_id
            keyboard.add(
                Text(
                    _label(f"{mode.button_label}{' ✅' if is_current else ''}"),
                    payload(Cmd.SET_MODE, mode=mode.id),
                ),
                KeyboardButtonColor.POSITIVE if is_current else KeyboardButtonColor.SECONDARY,
            )
        return keyboard.get_json()

    @cached_property
    def settings(self) -> str:
        return (
            Keyboard(inline=True)
            .add(Text("🎭 Режим общения", payload(Cmd.MODES)), KeyboardButtonColor.PRIMARY)
            .row()
            .add(Text("✏️ Переименовать диалог", payload(Cmd.RENAME_DIALOG)), KeyboardButtonColor.SECONDARY)
            .row()
            .add(Text("🧹 Очистить историю", payload(Cmd.CLEAR_HISTORY)), KeyboardButtonColor.NEGATIVE)
            .row()
            .add(Text("🤖 О модели", payload(Cmd.MODEL_INFO)), KeyboardButtonColor.SECONDARY)
            .get_json()
        )

    @cached_property
    def confirm_clear(self) -> str:
        return (
            Keyboard(inline=True)
            .add(Text("🧹 Да, очистить", payload(Cmd.CONFIRM_CLEAR)), KeyboardButtonColor.NEGATIVE)
            .add(Text("↩️ Отмена", payload(Cmd.CANCEL)), KeyboardButtonColor.SECONDARY)
            .get_json()
        )

    @cached_property
    def cancel(self) -> str:
        return (
            Keyboard(inline=True)
            .add(Text("↩️ Отмена", payload(Cmd.CANCEL)), KeyboardButtonColor.SECONDARY)
            .get_json()
        )


def _label(text: str) -> str:
    return truncate(text, LABEL_LIMIT)
