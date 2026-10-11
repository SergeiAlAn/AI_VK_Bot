from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatMode:
    """Режим общения (роль ассистента) — по сути именованный system prompt."""

    id: str
    title: str
    emoji: str
    description: str
    system_prompt: str
    # Короткое название для кнопки: кнопки режимов стоят по две в ряд
    short_title: str = ""

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.title}"

    @property
    def button_label(self) -> str:
        return f"{self.emoji} {self.short_title or self.title}"
