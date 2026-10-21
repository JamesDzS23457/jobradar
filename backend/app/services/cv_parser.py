import io
import json
import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SKILLS: list[dict[str, Any]] = json.loads((DATA_DIR / "skills.json").read_text(encoding="utf-8"))

ALIASES: dict[str, str] = {}
for item in SKILLS:
    for alias in [item["name"], *item.get("aliases", [])]:
        ALIASES[alias.lower()] = item["name"]


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _iter_docx_blocks(document: Document):
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _docx_text(document: Document) -> str:
    chunks: list[str] = []
    for block in _iter_docx_blocks(document):
        if isinstance(block, Paragraph):
            value = block.text.strip()
            if value:
                chunks.append(value)
        else:
            for row in block.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    chunks.append(" | ".join(dict.fromkeys(cells)))
    return "\n".join(chunks)


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ValueError("El PDF está protegido con contraseña.") from exc
        pages: list[str] = []
        for page in reader.pages:
            try:
                # Layout mode preserves columns and line breaks better than the
                # default extraction for most CV templates.
                value = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                value = page.extract_text() or ""
            if value.strip():
                pages.append(value)
        text = _clean_text("\n".join(pages))
        if not text:
            raise ValueError(
                "No se encontró texto en el PDF. Si es un PDF escaneado, súbelo como DOCX o "
                "convierte el escaneo a PDF con texto seleccionable."
            )
        return text
    if suffix == ".docx":
        document = Document(io.BytesIO(content))
        return _clean_text(_docx_text(document))
    if suffix in {".txt", ".md"}:
        return _clean_text(content.decode("utf-8", errors="ignore"))
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


def extract_links(text: str) -> dict[str, str]:
    links: dict[str, str] = {}
    urls = re.findall(r"https?://[^\s<>)\"']+|(?:www\.)[^\s<>)\"']+", text, flags=re.I)
    for raw in urls:
        url = raw.rstrip(".,;")
        if not url.lower().startswith("http"):
            url = f"https://{url}"
        lowered = url.lower()
        if "linkedin.com" in lowered:
            links.setdefault("LinkedIn", url)
        elif "github.com" in lowered:
            links.setdefault("GitHub", url)
        elif any(host in lowered for host in ("portfolio", "behance.net", "dribbble.com")):
            links.setdefault("Portafolio", url)
    return links


_DATE_RANGE = re.compile(
    r"((?:19|20)\d{2}|(?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2})"
    r"\s*(?:-|–|—|to|a|hasta)\s*"
    r"((?:19|20)\d{2}|(?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2}|presente|actual|present|now)",
    flags=re.I,
)
_BULLET = re.compile(r"^[-•*·▪◦]\s*(.+)$")


def _looks_like_heading(line: str, words: tuple[str, ...]) -> bool:
    normalized = line.lower().strip(" :")
    return any(normalized == word or normalized.startswith(f"{word} ") for word in words)


def _section_lines(lines: list[str], start_words: tuple[str, ...], stop_words: tuple[str, ...]) -> list[str]:
    inside = False
    result: list[str] = []
    for line in lines:
        if _looks_like_heading(line, start_words):
            inside = True
            continue
        if inside and _looks_like_heading(line, stop_words):
            break
        if inside:
            result.append(line)
    return result


def _split_role_company(line: str) -> tuple[str, str]:
    clean = _DATE_RANGE.sub("", line).strip(" -–—|·")
    for separator in (" | ", " — ", " – ", " @ ", " en "):
        if separator in clean:
            left, right = clean.split(separator, 1)
            return left.strip(), right.strip()
    return clean, ""


def extract_experience(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section = _section_lines(
        lines,
        ("experiencia", "experiencia laboral", "work experience", "professional experience"),
        ("educación", "education", "habilidades", "skills", "idiomas", "languages", "proyectos", "projects"),
    )
    source = section or lines
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in source:
        date_match = _DATE_RANGE.search(line)
        bullet_match = _BULLET.match(line)
        if date_match and not bullet_match and len(line) <= 160:
            role, company = _split_role_company(line)
            current = {
                "company": company,
                "role": role,
                "dates": f"{date_match.group(1)} - {date_match.group(2)}",
                "bullets": [],
            }
            items.append(current)
            continue
        if current is not None:
            value = bullet_match.group(1) if bullet_match else line
            if len(value) > 12:
                current["bullets"].append(value.strip())
    items = [item for item in items if item["role"] or item["company"] or item["bullets"]]
    if items:
        for item in items:
            item["bullets"] = item["bullets"][:12]
        return items[:8]

    bullets = [match.group(1).strip() for line in lines if (match := _BULLET.match(line))]
    if bullets:
        return [{"company": "Experiencia", "role": "", "dates": "", "bullets": bullets[:12]}]
    return []


def extract_education(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section = _section_lines(
        lines,
        ("educación", "education", "formación", "formacion", "estudios"),
        ("experiencia", "experience", "habilidades", "skills", "idiomas", "languages", "certificaciones"),
    )
    source = section or lines
    education: list[dict[str, Any]] = []
    institution_words = ("universidad", "university", "instituto", "institute", "colegio", "politécnico", "politecnico")
    degree_words = ("ingenier", "licenciat", "técnic", "tecnic", "tecnólog", "tecnolog", "bachelor", "master", "máster", "phd", "doctor")
    for index, line in enumerate(source):
        lowered = line.lower()
        if any(word in lowered for word in institution_words) or any(word in lowered for word in degree_words):
            dates = _DATE_RANGE.search(line)
            dates_text = f"{dates.group(1)} - {dates.group(2)}" if dates else ""
            institution = line
            degree = ""
            for separator in (" — ", " – ", " | ", " - "):
                if separator in line:
                    left, right = line.split(separator, 1)
                    if any(word in left.lower() for word in institution_words):
                        institution, degree = left.strip(), right.strip()
                    else:
                        degree, institution = left.strip(), right.strip()
                    break
            if not degree and index + 1 < len(source):
                next_line = source[index + 1]
                if any(word in next_line.lower() for word in degree_words):
                    degree = next_line
            education.append(
                {
                    "institution": _DATE_RANGE.sub("", institution).strip(" -–—|·"),
                    "degree": _DATE_RANGE.sub("", degree).strip(" -–—|·"),
                    "dates": dates_text,
                }
            )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in education:
        key = (item["institution"].lower(), item["degree"].lower())
        if key not in seen and (item["institution"] or item["degree"]):
            seen.add(key)
            deduped.append(item)
    return deduped[:6]


def parse_profile_heuristic(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = " ".join(lines[:8])[:900]
    headline = ""
    for line in lines[1:6]:
        if "@" in line or re.search(r"\+?\d[\d\s().-]{7,}\d", line):
            continue
        if 3 <= len(line) <= 120 and "|" not in line:
            headline = line
            break
    location = "Bogotá, Colombia"
    for line in lines[:12]:
        if re.search(r"(bogotá|bogota|medellín|medellin|cali|colombia|remote|remoto)", line, re.I):
            if len(line) <= 100:
                location = line
                break
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "location": location,
        "headline": headline,
        "summary": summary,
        "skills": find_skills(text),
        "experience": extract_experience(text),
        "education": extract_education(text),
        "languages": extract_languages(text),
        "links": extract_links(text),
        "years_experience": extract_years_experience(text),
        "raw_cv_text": text,
    }
