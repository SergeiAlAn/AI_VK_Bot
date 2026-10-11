import re

_SEPARATORS = ("\n\n", "\n", ". ", " ")
_WHITESPACE = re.compile(r"\s+")


def split_text(text: str, limit: int) -> list[str]:
    """Делит длинный текст на части не длиннее limit.

    Сначала пытается резать по абзацам, затем по строкам, предложениям и словам,
    чтобы не разрывать слова и блоки кода посередине.
    """
    text = text.strip()
    if limit <= 0:
        raise ValueError("limit must be positive")

    chunks: list[str] = []
    while len(text) > limit:
        cut = _find_cut(text, limit)
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def _find_cut(text: str, limit: int) -> int:
    window = text[:limit]
    for separator in _SEPARATORS:
        index = window.rfind(separator)
        # Не режем слишком близко к началу — иначе получатся «обрывки»
        if index >= limit // 2:
            return index + len(separator)
    return limit


def truncate(text: str, limit: int, suffix: str = "…") -> str:
    text = _WHITESPACE.sub(" ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - len(suffix), 0)].rstrip() + suffix
