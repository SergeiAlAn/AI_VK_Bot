"""Все тексты интерфейса бота. Держим их в одном месте, чтобы UX правился без поиска по коду."""

from collections.abc import Callable, Sequence

from models.chat import Role
from models.dialog import Dialog
from models.mode import ChatMode
from services.ai import (
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
from utils.text import truncate

THINKING = "🤔 Думаю над ответом…"

WELCOME = (
    "👋 Привет! Я AI-ассистент на базе нейросети.\n\n"
    "Просто напишите вопрос — и я отвечу. Я помню контекст разговора, "
    "умею вести несколько независимых диалогов и общаться в разных ролях.\n\n"
    "Кнопки внизу:\n"
    "🆕 Новый диалог — начать разговор с чистого листа\n"
    "📂 Список диалогов — переключиться, переименовать или удалить\n"
    "🎭 Сменить режим — выбрать роль: программист, преподаватель и др.\n"
    "⚙️ Настройки — модель, очистка истории\n"
    "❓ Помощь — подробная инструкция"
)

HELP = (
    "❓ Как пользоваться ботом\n\n"
    "💬 Общение\n"
    "Пишите сообщения как обычному собеседнику. Я помню последние {history} сообщений "
    "текущего диалога, поэтому можно задавать уточняющие вопросы.\n\n"
    "📂 Диалоги\n"
    "У каждого диалога своя история и свой режим. Удобно держать отдельные диалоги "
    "под разные темы: работа, учёба, личное. Новый диалог — кнопка «🆕 Новый диалог», "
    "все диалоги — «📂 Список диалогов» (✅ — текущий, 🗑 — удалить).\n\n"
    "🎭 Режимы\n"
    "{modes}\n"
    "Режим меняется только у текущего диалога, история при этом сохраняется.\n\n"
    "📎 Файлы\n"
    "Объёмные результаты — программу тренировок, план занятий, список слов, таблицу — "
    "я пришлю текстовым файлом. Можно и попросить прямо: «пришли это файлом». "
    "Чтобы доработать файл, просто напишите, что изменить.\n\n"
    "⚙️ Настройки\n"
    "Переименование диалога, очистка истории, информация о модели.\n\n"
    "⌨️ Команды текстом: «меню», «помощь», «отмена»."
)

MENU = "📋 Главное меню. Выберите действие кнопкой или просто напишите вопрос."
OLD_KEYBOARD = (
    "🔄 Эта кнопка устарела — меню обновилось!\n"
    "Пользуйтесь новыми кнопками внизу или просто напишите вопрос."
)
CANCELLED = "↩️ Действие отменено."

EMPTY_MESSAGE = "✍️ Сообщение пустое. Напишите текстом, что вас интересует."
NON_TEXT_MESSAGE = "📎 Пока я понимаю только текст. Опишите вопрос словами, пожалуйста."
TOO_LONG = (
    "📏 Сообщение слишком длинное: {length} символов (максимум — {limit}).\n"
    "Сократите его или разбейте на несколько частей."
)
BUSY = "⏳ Я ещё отвечаю на предыдущее сообщение. Подождите немного, пожалуйста."
TRUNCATED_NOTE = "\n\n✂️ Ответ получился слишком длинным и был обрезан. Напишите «продолжи», чтобы получить окончание."
ANSWER_IN_OTHER_DIALOG = "💬 Ответ в диалоге «{title}»:\n\n"
FILES_READY = "📎 Готово! Отправляю файл."
FILE_CAPTION = "📎 {name}"
FILE_UPLOAD_FAILED = "⚠️ Не получилось прикрепить файл «{name}», поэтому присылаю его содержимое текстом:\n\n"

DIALOG_CREATED = (
    "🆕 Создан новый диалог «{title}».\n"
    "Режим: {mode}\n\n"
    "Напишите первое сообщение — по нему я автоматически придумаю название."
)
DIALOG_LIMIT = (
    "📦 Достигнут лимит диалогов ({limit}). "
    "Удалите ненужные в «📂 Список диалогов», чтобы создать новый."
)
DIALOG_NOT_FOUND = "🤷 Этот диалог не найден — возможно, он уже удалён. Откройте «📂 Список диалогов» заново."
CONFIRM_DELETE = "🗑 Удалить диалог «{title}» ({count} сообщ.)?\nЭто действие нельзя отменить."
RENAME_PROMPT = (
    "✏️ Введите новое название для диалога «{title}» (до {limit} символов).\n"
    "Или нажмите «Отмена»."
)
RENAME_INVALID = "⚠️ Название должно содержать от 1 до {limit} символов. Попробуйте ещё раз."
RENAMED = "✅ Диалог переименован в «{title}»."

MODE_CHANGED = (
    "🎭 Режим диалога «{title}» изменён на {mode}.\n\n"
    "{description}\n\n"
    "Новый стиль применится со следующего сообщения. История диалога сохранена."
)
CONFIRM_CLEAR = "🧹 Очистить историю диалога «{title}» ({count} сообщ.)?\nМодель забудет весь контекст этого разговора."
HISTORY_CLEARED = "🧹 История диалога «{title}» очищена ({count} сообщ.). Начинаем с чистого листа!"
HISTORY_ALREADY_EMPTY = "📭 В диалоге «{title}» пока нет сообщений — очищать нечего."

UNEXPECTED_ERROR = "😔 Что-то пошло не так. Попробуйте ещё раз чуть позже."


def help_text(modes: Sequence[ChatMode], history: int) -> str:
    modes_text = "\n".join(f"{m.label} — {m.description}" for m in modes)
    return HELP.format(modes=modes_text, history=history)


def dialogs_list(
    dialogs: Sequence[Dialog],
    active_id: str | None,
    modes: dict[str, ChatMode],
    page: int,
    page_size: int,
    pages: int,
    limit: int,
) -> str:
    page = min(max(page, 0), pages - 1)
    start = page * page_size
    lines = [f"📂 Ваши диалоги: {len(dialogs)} из {limit}" + (f" · стр. {page + 1}/{pages}" if pages > 1 else "")]
    lines.append("")
    for number, dialog in enumerate(dialogs[start : start + page_size], start=start + 1):
        mark = "✅" if dialog.id == active_id else "💬"
        mode = modes.get(dialog.mode)
        mode_label = mode.emoji if mode else "❔"
        lines.append(f"{mark} {number}. {dialog.title} — {mode_label} · {len(dialog.messages)} сообщ.")
    lines.append("")
    lines.append("Нажмите на диалог, чтобы переключиться, или 🗑, чтобы удалить.")
    return "\n".join(lines)


def switched(dialog: Dialog, mode: ChatMode, preview: Callable[[str], str]) -> str:
    text = f"✅ Вы перешли в диалог «{dialog.title}».\nРежим: {mode.label} · сообщений: {len(dialog.messages)}"
    last = next((m for m in reversed(dialog.messages) if m.role is Role.ASSISTANT), None)
    if last is not None:
        text += f"\n\n💭 Последний ответ:\n{truncate(preview(last.content), 300)}"
    else:
        text += "\n\nДиалог пока пустой — напишите сообщение."
    return text


def dialog_deleted(title: str, active: Dialog, created_new: bool) -> str:
    text = f"🗑 Диалог «{title}» удалён."
    if created_new:
        text += f"\nЭто был последний диалог, поэтому я создал новый: «{active.title}»."
    else:
        text += f"\nТекущий диалог: «{active.title}»."
    return text


def modes_list(modes: Sequence[ChatMode], current: ChatMode, dialog: Dialog) -> str:
    lines = [f"🎭 Режим общения для диалога «{dialog.title}»", f"Сейчас: {current.label}", ""]
    lines.extend(f"{m.label} — {m.description}" for m in modes)
    lines += ["", "Выберите новый режим кнопкой ниже 👇"]
    return "\n".join(lines)


def settings(dialog: Dialog, mode: ChatMode, model: str, max_history: int, dialogs_count: int) -> str:
    return (
        "⚙️ Настройки\n\n"
        f"💬 Текущий диалог: «{dialog.title}»\n"
        f"🎭 Режим: {mode.label}\n"
        f"🧠 Память: {len(dialog.messages)} из {max_history} сообщений\n"
        f"📂 Всего диалогов: {dialogs_count}\n"
        f"🤖 Модель: {model}"
    )


def model_info(model: str, fallbacks: Sequence[str], max_history: int) -> str:
    text = (
        "🤖 О модели\n\n"
        f"Основная модель: {model}\n"
        "Подключение: ProxyAPI.ru (OpenAI-совместимый API)\n"
        f"Контекст: последние {max_history} сообщений текущего диалога + инструкция режима."
    )
    if fallbacks:
        text += f"\nРезервные модели: {', '.join(fallbacks)} — используются, если основная временно недоступна."
    return text


def ai_error(error: AIError) -> str:
    """Понятное пользователю сообщение (fallback) вместо технической ошибки API."""
    match error:
        case AITimeoutError():
            return "⌛ Модель слишком долго думала и не успела ответить. Попробуйте ещё раз или упростите вопрос."
        case AINetworkError():
            return "📡 Не удалось связаться с сервером нейросети. Проверьте позже — обычно это временно."
        case AIRateLimitError():
            return "🚦 Сейчас слишком много запросов. Подождите минуту и повторите."
        case AIUnavailableError() | AIModelNotFoundError():
            return "🛠 Нейросеть временно недоступна. Попробуйте через пару минут."
        case AIEmptyResponseError():
            return "🤐 Модель вернула пустой ответ. Попробуйте переформулировать вопрос."
        case AIBadRequestError():
            return (
                "⚠️ Модель не смогла обработать запрос. Если диалог очень длинный — "
                "очистите историю в «⚙️ Настройки» или начните новый диалог."
            )
        case AIQuotaError() | AIAuthError() | AIAccessDeniedError():
            return "🔧 Ассистент временно недоступен по техническим причинам. Мы уже разбираемся."
        case _:
            return UNEXPECTED_ERROR
