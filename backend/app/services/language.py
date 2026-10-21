"""Language requirement detection for job postings.

The goal is conservative: only detect English/Spanish when the posting appears
to require it. Phrases such as "English is a plus" are ignored.
"""

from __future__ import annotations

import re

LANGUAGE_PATTERNS = {
    "Inglés": r"(?:english|inglés|ingles)",
    "Español": r"(?:spanish|español|espanol)",
}

LEVEL_VALUES = ("a1", "a2", "b1", "b2", "c1", "c2")

NEGATIVE_MARKERS = (
    "plus",
    "nice to have",
    "deseable",
    "no requerido",
    "no obligatorio",
    "not required",
    "not mandatory",
    "is a bonus",
    "es un plus",
)

REQUIRED_MARKERS = (
    "required",
    "mandatory",
    "essential",
    "obligatorio",
    "requerido",
    "indispensable",
    "excluyente",
)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?;])\s+|,\s*|\n+", text or "") if part.strip()]


def _level_from_text(text: str, language_pattern: str) -> str:
    # "English B2", "Inglés: B2", "B2 English", "nivel B2 de inglés".
    patterns = (
        rf"{language_pattern}\s*(?:level|nivel)?\s*[:\-]?\s*({ '|'.join(LEVEL_VALUES) })\b",
        rf"\b({ '|'.join(LEVEL_VALUES) })\s*(?:level|nivel)?\s*(?:of\s*|de\s*)?{language_pattern}\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return match.group(1).upper()
    return ""


def infer_job_languages(text: str) -> dict[str, str]:
    """Return explicitly required languages and levels.

    A posting that only says "English is a plus" returns no requirement.
    Explicit levels win over generic "required"/"fluent" wording.
    """
    result: dict[str, str] = {}
    for sentence in _sentences(text):
        normalized = sentence.lower()
        for language, language_pattern in LANGUAGE_PATTERNS.items():
            if not re.search(language_pattern, normalized, flags=re.I):
                continue
            if any(marker in normalized for marker in NEGATIVE_MARKERS):
                continue
            level = _level_from_text(sentence, language_pattern)
            if not level:
                if re.search(r"\b(fluent|fluidez|avanzado|advanced|c1)\b", normalized):
                    level = "C1"
                elif re.search(
                    rf"\b({'|'.join(REQUIRED_MARKERS)})\b",
                    normalized,
                    flags=re.I,
                ):
                    level = "B2"
                elif re.search(r"\b(intermediate|intermedio|b1|b2)\b", normalized):
                    level = "B2"
                elif re.search(r"\b(basic|básico|basico|a1|a2)\b", normalized):
                    level = "A2"
            if level:
                existing = result.get(language, "")
                if not existing or LEVEL_VALUES.index(level.lower()) > LEVEL_VALUES.index(existing.lower()):
                    result[language] = level
    return result
