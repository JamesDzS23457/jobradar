import io
import json
import re
from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SKILLS: list[dict[str, Any]] = json.loads((DATA_DIR / "skills.json").read_text(encoding="utf-8"))

ALIASES: dict[str, str] = {}
for item in SKILLS:
    for alias in [item["name"], *item.get("aliases", [])]:
        ALIASES[alias.lower()] = item["name"]


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if suffix == ".docx":
        document = Document(io.BytesIO(content))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
    if suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore").strip()
    raise ValueError("Formato no soportado. Usa PDF, DOCX, TXT o MD.")


def find_skills(text: str) -> list[str]:
    normalized = text.lower()
    found: list[str] = []
    for alias, canonical in ALIASES.items():
        if canonical in found:
            continue
        if len(alias) <= 2:
            pattern = rf"(?<![\w]){re.escape(alias)}(?![\w])"
            if re.search(pattern, normalized):
                found.append(canonical)
        elif alias in normalized:
            found.append(canonical)
    return sorted(found, key=str.lower)


def extract_email(text: str) -> str:
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"(\+?\d[\d\s().-]{7,}\d)", text)
    return match.group(0).strip() if match else ""


def extract_name(text: str) -> str:
    for line in text.splitlines()[:12]:
        clean = line.strip()
        if not clean or "@" in clean or re.search(r"\d{3,}", clean):
            continue
        if 3 <= len(clean) <= 60 and len(clean.split()) <= 6:
            return clean
    return ""


def extract_languages(text: str) -> dict[str, str]:
    languages: dict[str, str] = {}
    normalized = text.lower()
    patterns = {
        "Español": r"(español|spanish)\s*[:\-]?\s*(nativo|native|[abc][12])",
        "Inglés": r"(inglés|english)\s*[:\-]?\s*(nativo|native|[abc][12])",
    }
    for language, pattern in patterns.items():
        match = re.search(pattern, normalized)
        if match:
            level = match.group(2).upper()
            languages[language] = "Nativo" if level in {"NATIVO", "NATIVE"} else level
    if "Español" not in languages and ("español" in normalized or "spanish" in normalized):
        languages["Español"] = "Nativo"
    return languages


def extract_years_experience(text: str) -> int:
    matches = re.findall(r"(\d{1,2})\+?\s*(años|years)", text.lower())
    years = [int(value) for value, _ in matches]
    return max(years) if years else 0


def extract_experience(text: str) -> list[dict[str, Any]]:
    bullets = []
    for line in text.splitlines():
        clean = line.strip()
        if clean.startswith(("-", "•", "*", "·")) and len(clean) > 12:
            bullets.append(clean.lstrip("-•*· ").strip())
    if not bullets:
        return []
    return [
        {
            "company": "Experiencia",
            "role": "",
            "dates": "",
            "bullets": bullets[:12],
        }
    ]


def parse_profile_heuristic(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = " ".join(lines[:6])[:700]
    headline = ""
    for line in lines[1:5]:
        if "@" in line or re.search(r"\+?\d[\d\s().-]{7,}\d", line):
            continue
        if 3 <= len(line) <= 120 and "|" not in line:
            headline = line
            break
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "location": "Bogotá, Colombia",
        "headline": headline,
        "summary": summary,
        "skills": find_skills(text),
        "experience": extract_experience(text),
        "education": [],
        "languages": extract_languages(text),
        "links": {},
        "years_experience": extract_years_experience(text),
        "raw_cv_text": text,
    }
