"""Clean HTML fragments and common mojibake found in job descriptions."""

from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup


def _fix_mojibake(text: str) -> str:
    if not any(marker in text for marker in ("Ã", "Â", "â€")):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def clean_html_text(value: object, max_length: int | None = None) -> str:
    text = str(value or "")
    if "<" in text and ">" in text:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text("\n")
    text = unescape(text)
    text = _fix_mojibake(text)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text[:max_length] if max_length else text


def json_safe(value: object) -> object:
    """Convert dates and other common Python values into JSON-safe values."""
    from datetime import date, datetime
    from pathlib import Path

    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
