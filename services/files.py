"""Извлечение файлов из ответа модели.

Модель оформляет файл блоком <file name="...">...</file> (см. FILE_OUTPUT_INSTRUCTIONS).
Здесь блоки вырезаются из текста и превращаются в GeneratedFile — без привязки к VK,
поэтому отправку можно реализовать для любого мессенджера.
"""

import re
from dataclasses import dataclass
from pathlib import PurePath

_FILE_BLOCK = re.compile(
    r'<file\s+name\s*=\s*["\']?(?P<name>[^"\'>\n]*)["\']?\s*>\n?(?P<body>.*?)(?:\n?</file>|\Z)',
    re.DOTALL | re.IGNORECASE,
)
_UNSAFE_NAME_CHARS = re.compile(r"[^\w.\-]+", re.UNICODE)

# Excel и старый «Блокнот» корректно открывают кириллицу в CSV/TXT только с BOM
_ENCODINGS = {".txt": "utf-8-sig", ".csv": "utf-8-sig", ".md": "utf-8"}
DEFAULT_EXTENSION = ".txt"
FILE_PLACEHOLDER = "📎 {name}"


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    name: str
    content: str

    @property
    def extension(self) -> str:
        return PurePath(self.name).suffix.lower()

    def to_bytes(self) -> bytes:
        return self.content.encode(_ENCODINGS.get(self.extension, "utf-8"))


@dataclass(frozen=True, slots=True)
class ParsedReply:
    text: str
    files: tuple[GeneratedFile, ...]


class FileExtractor:
    def __init__(self, max_files: int = 3, max_file_chars: int = 200_000, max_name_length: int = 60) -> None:
        self._max_files = max_files
        self._max_file_chars = max_file_chars
        self._max_name_length = max_name_length

    def parse(self, raw: str) -> ParsedReply:
        """Возвращает текст без файловых блоков и список файлов.

        Незакрытый блок (ответ оборвался по лимиту токенов) тоже считается файлом —
        лучше выдать неполный документ, чем вывалить разметку в чат.
        """
        files: list[GeneratedFile] = []
        used_names: set[str] = set()

        def replace(match: re.Match[str]) -> str:
            body = match.group("body").strip("\n")
            if not body.strip():
                return ""
            if len(files) >= self._max_files:
                return body  # сверх лимита — оставляем содержимое обычным текстом
            name = self._unique(self._sanitize(match.group("name")), used_names)
            files.append(GeneratedFile(name=name, content=body[: self._max_file_chars]))
            return ""

        text = _FILE_BLOCK.sub(replace, raw)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return ParsedReply(text=text, files=tuple(files))

    def to_plain_text(self, raw: str) -> str:
        """Текст для превью: файловые блоки заменены на «📎 имя файла»."""
        return _FILE_BLOCK.sub(
            lambda m: FILE_PLACEHOLDER.format(name=self._sanitize(m.group("name"))), raw
        ).strip()

    def _sanitize(self, raw_name: str) -> str:
        name = PurePath(raw_name.strip().replace("\\", "/")).name  # отрезаем любые пути
        name = _UNSAFE_NAME_CHARS.sub("_", name).strip("._")
        stem, suffix = PurePath(name).stem, PurePath(name).suffix.lower()
        if suffix not in _ENCODINGS:
            # Неизвестное расширение (.exe, .py, без расширения) — отдаём как текст
            stem, suffix = name or "file", DEFAULT_EXTENSION
        stem = (stem or "file")[: self._max_name_length - len(suffix)]
        return f"{stem}{suffix}"

    @staticmethod
    def _unique(name: str, used: set[str]) -> str:
        candidate, index = name, 2
        path = PurePath(name)
        while candidate.lower() in used:
            candidate = f"{path.stem}_{index}{path.suffix}"
            index += 1
        used.add(candidate.lower())
        return candidate
