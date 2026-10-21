"""Import and normalize a public job posting from its original URL.

The importer prefers schema.org ``JobPosting`` structured data (JSON-LD),
which most modern job boards and company career pages expose. When that is
not available it falls back to OpenGraph/meta tags and the visible page text.
It never submits an application: the returned URL always points back to the
original portal so the user can apply there.
"""

from __future__ import annotations

import json
import logging
import re
from html import unescape
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.services.cv_parser import find_skills
from app.services.location import seniority_from_title
from app.services.text_clean import clean_html_text

logger = logging.getLogger(__name__)

MAX_HTML_BYTES = 5 * 1024 * 1024
MAX_DESCRIPTION_CHARS = 50_000
REQUEST_TIMEOUT = 25
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 JobRadar/0.1"
)

_SOURCE_ALIASES: dict[str, str] = {
    "linkedin.com": "linkedin",
    "indeed.com": "indeed",
    "computrabajo.com": "computrabajo",
    "elempleo.com": "elempleo",
    "magneto.com.co": "magneto",
    "getonbrd.com": "getonbrd",
    "torre.ai": "torre",
    "remotive.com": "remotive",
    "remoteok.com": "remoteok",
    "remoteok.io": "remoteok",
    "workana.com": "workana",
    "glassdoor.com": "glassdoor",
    "jobs.lever.co": "lever",
    "boards.greenhouse.io": "greenhouse",
    "job-boards.greenhouse.io": "greenhouse",
    "jobs.ashbyhq.com": "ashby",
    "apply.workable.com": "workable",
    "breezy.hr": "breezy",
    "teamtailor.com": "teamtailor",
}

_COUNTRY_NAMES = {
    "co": "Colombia",
    "us": "United States",
    "usa": "United States",
    "ca": "Canada",
    "mx": "Mexico",
    "ar": "Argentina",
    "cl": "Chile",
    "pe": "Peru",
    "br": "Brazil",
    "ec": "Ecuador",
    "uy": "Uruguay",
    "py": "Paraguay",
    "bo": "Bolivia",
    "ve": "Venezuela",
    "pa": "Panama",
    "cr": "Costa Rica",
    "do": "Dominican Republic",
    "sv": "El Salvador",
    "gt": "Guatemala",
    "hn": "Honduras",
    "ni": "Nicaragua",
    "pr": "Puerto Rico",
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "de": "Germany",
    "fr": "France",
    "es": "Spain",
    "worldwide": "Worldwide",
}

_LATAM_COUNTRIES = {
    "Colombia",
    "Mexico",
    "Argentina",
    "Chile",
    "Peru",
    "Brazil",
    "Ecuador",
    "Uruguay",
    "Paraguay",
    "Bolivia",
    "Venezuela",
    "Panama",
    "Costa Rica",
    "Dominican Republic",
    "El Salvador",
    "Guatemala",
    "Honduras",
    "Nicaragua",
    "Puerto Rico",
}

_GENERIC_TITLES = {
    "linkedin",
    "indeed",
    "computrabajo",
    "elempleo",
    "glassdoor",
    "facebook",
    "instagram",
    "login",
    "sign in",
    "iniciar sesión",
}


class JobImportError(ValueError):
    """A user-facing error while importing a job URL."""


class JobLinkOnlyError(JobImportError):
    """The link is valid but the portal blocks automatic reading/login is required."""


def _validate_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise JobImportError("El enlace debe empezar por http:// o https://.")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise JobImportError("El enlace no tiene un dominio válido.")
    if parsed.username or parsed.password:
        raise JobImportError("El enlace no puede incluir usuario o contraseña.")
    if host in {"localhost", "0.0.0.0", "::1"} or host.endswith(".local"):
        raise JobImportError("Por seguridad no se pueden importar enlaces internos.")
    try:
        address = ip_address(host)
    except ValueError:
        address = None
    if address is not None and (address.is_private or address.is_loopback or address.is_reserved):
        raise JobImportError("Por seguridad no se pueden importar direcciones de red privadas.")
    # Fragments are client-side only; keep the canonical page URL.
    return urlunparse(parsed._replace(fragment=""))


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("name") or value.get("value") or value.get("text") or ""
    if isinstance(value, list):
        value = " ".join(_as_text(item) for item in value if item)
    return unescape(str(value)).strip()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    result: list[str] = []
    for item in items:
        text = _as_text(item)
        if text and len(text) <= 80:
            result.append(text)
    return result


def _strip_html(value: Any) -> str:
    return clean_html_text(value, max_length=MAX_DESCRIPTION_CHARS)


def _clean_title(value: Any, company: str = "") -> str:
    title = _as_text(value)
    title = re.sub(r"^\s*\[(?:hiring|new|urgent|remoto|remote)\]\s*", "", title, flags=re.I)
    if company:
        escaped = re.escape(company.strip())
        title = re.sub(rf"\s*@\s*{escaped}\s*$", "", title, flags=re.I)
        title = re.sub(rf"\s+[|·\-–—]\s*{escaped}\s*$", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" -|·–—")
    return title[:240]


def _organization_name(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        return _as_text(value.get("name") or value.get("legalName"))
    return _as_text(value)


def _type_names(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    if isinstance(raw, str):
        return {raw.lower()}
    if isinstance(raw, list):
        return {str(item).lower() for item in raw}
    return set()


def _walk_jsonld(value: Any):
    if isinstance(value, dict):
        yield value
        for key in ("@graph", "mainEntity", "itemListElement", "hasPart"):
            child = value.get(key)
            if isinstance(child, (dict, list)):
                yield from _walk_jsonld(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_jsonld(item)


def _find_jobposting(payload: Any) -> dict[str, Any] | None:
    for node in _walk_jsonld(payload):
        if isinstance(node, dict) and "jobposting" in _type_names(node):
            return node
    return None


def _country_name(value: Any) -> str:
    if isinstance(value, dict):
        code = _as_text(value.get("name") or value.get("identifier") or value.get("addressCountry"))
        if code:
            return _COUNTRY_NAMES.get(code.lower(), code)
        value = value.get("addressCountry")
    text = _as_text(value)
    if not text:
        return ""
    return _COUNTRY_NAMES.get(text.lower(), text)


def _address_parts(address: Any) -> tuple[str, str, str]:
    if isinstance(address, dict):
        city = _as_text(address.get("addressLocality"))
        region = _as_text(address.get("addressRegion"))
        country = _country_name(address.get("addressCountry"))
        return city, region, country
    text = _as_text(address)
    return "", "", _COUNTRY_NAMES.get(text.lower(), text)


def _applicant_countries(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    countries: list[str] = []
    for item in values:
        name = _country_name(item)
        if name and name not in countries:
            countries.append(name)
    return countries


def _location_from_jsonld(node: dict[str, Any], description: str) -> dict[str, str]:
    locations = node.get("jobLocation")
    if isinstance(locations, dict):
        locations = [locations]
    if not isinstance(locations, list):
        locations = []

    cities: list[str] = []
    regions: list[str] = []
    countries: list[str] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        city, region, country = _address_parts(location.get("address"))
        if not any((city, region, country)):
            city = _as_text(location.get("name"))
        if city:
            cities.append(city)
        if region:
            regions.append(region)
        if country:
            countries.append(country)

    remote_value = _as_text(node.get("jobLocationType")).lower()
    is_remote = "telecommute" in remote_value or "remote" in remote_value
    applicant_countries = _applicant_countries(node.get("applicantLocationRequirements"))

    city = cities[0] if cities else ""
    country = countries[0] if countries else ""
    if applicant_countries:
        if all(name in {"United States", "Canada"} for name in applicant_countries):
            country = "United States"
            remote_scope = "us_only"
        elif "Colombia" in applicant_countries:
            country = "Colombia"
            remote_scope = "colombia"
        elif any(name in _LATAM_COUNTRIES for name in applicant_countries):
            country = country or "Latinoamérica"
            remote_scope = "latam"
        elif "Worldwide" in applicant_countries:
            country = "Worldwide"
            remote_scope = "global"
        else:
            remote_scope = ""
    else:
        remote_scope = ""

    location_text = ", ".join(part for part in [city, regions[0] if regions else "", country] if part)
    if is_remote:
        if not location_text:
            location_text = "Remoto"
        if country == "Colombia":
            location_text = "Remoto (Colombia)"
        elif remote_scope == "latam":
            location_text = "Remoto (LatAm)"
        elif remote_scope == "us_only":
            location_text = "Remoto (US/Canadá)"
        elif remote_scope == "global":
            location_text = "Remoto"
        elif description:
            lower = description.lower()
            if "colombia" in lower or "bogotá" in lower or "bogota" in lower:
                country = "Colombia"
                remote_scope = "colombia"
                location_text = "Remoto (Colombia)"
            elif "worldwide" in lower or "anywhere" in lower:
                country = "Worldwide"
                remote_scope = "global"
                location_text = "Remoto"

    return {
        "location_text": location_text,
        "city": city,
        "country": country,
        "remote_type": "remote" if is_remote else "",
        "remote_scope": remote_scope,
    }


def _salary_from_jsonld(value: Any) -> tuple[int | None, int | None, str]:
    if not isinstance(value, dict):
        return None, None, "COP"
    currency = _as_text(value.get("currency")).upper() or "COP"
    salary = value.get("value")
    unit = ""
    if isinstance(salary, dict):
        unit = _as_text(salary.get("unitText")).upper()
        minimum = salary.get("minValue") if salary.get("minValue") is not None else salary.get("value")
        maximum = salary.get("maxValue") if salary.get("maxValue") is not None else salary.get("value")
    else:
        minimum = salary
        maximum = salary
        unit = _as_text(value.get("unitText")).upper()

    def to_int(raw: Any) -> int | None:
        if raw in (None, ""):
            return None
        if isinstance(raw, (int, float)):
            return int(round(raw))
        text = str(raw).strip()
        try:
            return int(round(float(text.replace(",", ""))))
        except (TypeError, ValueError):
            try:
                return int(round(float(text.replace(".", "").replace(",", "."))))
            except (TypeError, ValueError):
                return None

    minimum_int = to_int(minimum)
    maximum_int = to_int(maximum)
    if minimum_int is None and maximum_int is None:
        return None, None, currency

    # The UI shows monthly COP and annual USD. Harmonize values so salary
    # matching is meaningful across portals that publish hourly/yearly data.
    if unit in {"HOUR", "HOURLY"}:
        factor = 2080
        minimum_int = minimum_int * factor if minimum_int else None
        maximum_int = maximum_int * factor if maximum_int else None
    elif unit in {"DAY", "DAILY"}:
        factor = 260
        minimum_int = minimum_int * factor if minimum_int else None
        maximum_int = maximum_int * factor if maximum_int else None
    elif unit in {"WEEK", "WEEKLY"}:
        factor = 52
        minimum_int = minimum_int * factor if minimum_int else None
        maximum_int = maximum_int * factor if maximum_int else None
    elif unit in {"MONTH", "MONTHLY"}:
        if currency != "COP":
            minimum_int = minimum_int * 12 if minimum_int else None
            maximum_int = maximum_int * 12 if maximum_int else None
    elif unit in {"YEAR", "ANNUAL", "YEARLY"}:
        if currency == "COP":
            minimum_int = int(minimum_int / 12) if minimum_int else None
            maximum_int = int(maximum_int / 12) if maximum_int else None
    return minimum_int, maximum_int, currency


def _years_from_experience(value: Any) -> int:
    if isinstance(value, dict):
        months = value.get("monthsOfExperience")
        try:
            if months is not None:
                return max(0, round(float(months) / 12))
        except (TypeError, ValueError):
            pass
        value = value.get("description")
    text = _as_text(value)
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|años?)", text, re.I)
    if match:
        return max(0, int(round(float(match.group(1).replace(",", ".")))))
    return 0


def _payload_from_jsonld(node: dict[str, Any], page_url: str) -> dict[str, Any]:
    company = _organization_name(node.get("hiringOrganization"))
    description = _strip_html(node.get("description"))
    title = _clean_title(node.get("title") or node.get("name"), company)
    location = _location_from_jsonld(node, description)
    salary_min, salary_max, currency = _salary_from_jsonld(node.get("baseSalary"))
    skills = _as_list(node.get("skills"))
    if not skills:
        skills = find_skills(f"{title} {description}")[:12]
    identifier = node.get("identifier")
    if isinstance(identifier, dict):
        identifier = identifier.get("value") or identifier.get("name") or page_url
    external_id = _as_text(identifier) or page_url

    return {
        "source": _source_from_url(page_url),
        "external_id": external_id,
        "title": title,
        "company": company or _domain_company(page_url),
        "description": description,
        "location_text": location["location_text"],
        "city": location["city"],
        "country": location["country"],
        "remote_type": location["remote_type"],
        "remote_scope": location["remote_scope"],
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": currency,
        "url": page_url,
        "posted_at": node.get("datePosted") or node.get("dateModified"),
        "skills_required": skills,
        "skills_nice": [],
        "seniority": seniority_from_title(title),
        "years_experience": _years_from_experience(node.get("experienceRequirements")),
        "languages": {},
        "red_flags": [],
    }


def _meta_content(soup: BeautifulSoup, *keys: str) -> str:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return _as_text(tag.get("content"))
    return ""


def _visible_text(soup: BeautifulSoup) -> str:
    root = soup.find("main") or soup.find("article") or soup.body
    if root is None:
        return ""
    for tag in root.find_all(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    text = root.get_text("\n", strip=True)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _payload_from_metadata(soup: BeautifulSoup, page_url: str) -> dict[str, Any]:
    title = _meta_content(soup, "og:title", "twitter:title")
    if not title and soup.h1:
        title = _as_text(soup.h1.get_text(" ", strip=True))
    if not title and soup.title:
        title = _as_text(soup.title.get_text(" ", strip=True))
    company = _meta_content(soup, "og:site_name", "application-name") or _domain_company(page_url)
    title = _clean_title(title, company)
    description = _meta_content(soup, "og:description", "twitter:description", "description")
    if len(description) < 160:
        visible = _visible_text(soup)
        if visible:
            description = f"{description}\n{visible}".strip()
    description = _strip_html(description)
    location_text = _meta_content(soup, "job:location", "og:locality")
    combined = f"{title} {description}".lower()
    if any(marker in combined for marker in ("sign in to view", "inicia sesión para ver", "authwall")):
        raise JobLinkOnlyError(
            "Ingresa al portal para postularte: este enlace requiere iniciar sesión "
            "para mostrar la vacante."
        )
    if not title or title.lower() in _GENERIC_TITLES:
        raise JobImportError(
            "No se pudo leer el título de la vacante en ese enlace. Comprueba que sea una oferta pública."
        )

    return {
        "source": _source_from_url(page_url),
        "external_id": page_url,
        "title": title,
        "company": company,
        "description": description,
        "location_text": location_text,
        "city": "",
        "country": "",
        "remote_type": "",
        "remote_scope": "",
        "url": page_url,
        "posted_at": _meta_content(soup, "article:published_time", "datePublished", "date"),
        "skills_required": find_skills(f"{title} {description}")[:12],
        "skills_nice": [],
        "seniority": seniority_from_title(title),
        "years_experience": 0,
        "languages": {},
        "red_flags": [],
    }


def _source_from_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    for domain, name in _SOURCE_ALIASES.items():
        if host == domain or host.endswith(f".{domain}"):
            return name
    return host.split(".")[0] if host else "web"


def _domain_company(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host.split(".")[0].replace("-", " ").title() if host else ""


def _title_company_from_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    slug = parts[-1] if parts else ""
    if slug.lower() in {"jobs", "job", "view", "apply", "vacante", "oferta"} and len(parts) > 1:
        slug = parts[-2]
    slug = re.sub(r"\.(?:html?|php|aspx?)$", "", slug, flags=re.I)
    slug = re.sub(r"[-_]?\d{5,}$", "", slug)
    slug = re.sub(r"[-_]+", " ", slug).strip()
    if not slug:
        return "", ""
    company = ""
    lower = slug.lower()
    if " at " in lower:
        index = lower.index(" at ")
        title, company = slug[:index], slug[index + 4 :]
    elif " en " in lower:
        index = lower.index(" en ")
        title, company = slug[:index], slug[index + 4 :]
    else:
        title = slug
    title = re.sub(r"^(?:oferta de trabajo de|oferta de empleo de|empleo de)\s+", "", title, flags=re.I)
    clean_title = _clean_title(title.title())
    clean_company = _clean_title(company.title()) if company else ""
    return clean_title, clean_company


def link_only_payload(raw_url: str, note: str = "", portal_label: str = "", collector: str = "manual") -> dict[str, Any]:
    """Build a safe placeholder for a public link that cannot be read automatically."""
    url = _validate_url(raw_url)
    title, company = _title_company_from_url(url)
    domain_company = _domain_company(url)
    company = company or domain_company
    if not title:
        title = f"Vacante en {portal_label or company or 'el portal'}"
    access_note = note or (
        "Ingresa al portal para postularte: este enlace requiere inicio de sesión "
        "o no permite leer la vacante automáticamente."
    )
    description = (
        f"{access_note}\n\n"
        "JobRadar conservó el enlace original para que puedas abrirlo, revisar la vacante "
        "y postularte directamente en el portal."
    )
    return {
        "source": _source_from_url(url),
        "collector": collector,
        "external_id": url,
        "title": title,
        "company": company,
        "description": description,
        "location_text": "No especificada",
        "city": "",
        "country": "",
        "remote_type": "unknown",
        "remote_scope": "unknown",
        "salary_min": None,
        "salary_max": None,
        "currency": "COP",
        "url": url,
        "posted_at": None,
        "skills_required": find_skills(f"{title} {description}")[:12],
        "skills_nice": [],
        "seniority": seniority_from_title(title),
        "years_experience": 0,
        "languages": {},
        "red_flags": ["Requiere iniciar sesión en el portal"],
        "link_only": True,
        "requires_login": True,
        "access_note": access_note,
    }


def extract_job_from_html(html: str, page_url: str) -> tuple[dict[str, Any], str]:
    """Extract a job payload and the extraction method from public HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        if "ld+json" not in script_type:
            continue
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.debug("Ignoring invalid JSON-LD on %s", page_url)
            continue
        job_posting = _find_jobposting(payload)
        if job_posting is not None:
            extracted = _payload_from_jsonld(job_posting, page_url)
            if extracted["title"]:
                return extracted, "jsonld"
    return _payload_from_metadata(soup, page_url), "metadata"


def import_job_from_url(raw_url: str) -> tuple[dict[str, Any], str]:
    """Fetch a public job page and return (payload, extraction_method)."""
    url = _validate_url(raw_url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in {401, 403, 429, 999}:
            raise JobLinkOnlyError(
                "Ingresa al portal para postularte: este enlace requiere iniciar sesión "
                "o bloquea la lectura automática."
            ) from exc
        raise JobImportError(
            f"El portal respondió {status}. La vacante puede estar cerrada o "
            "requerir inicio de sesión."
        ) from exc
    except httpx.HTTPError as exc:
        raise JobImportError(
            "No se pudo abrir el enlace. Revisa la URL y tu conexión a internet."
        ) from exc

    if len(response.content) > MAX_HTML_BYTES:
        raise JobImportError("La página es demasiado grande para analizarla automáticamente.")
    content_type = (response.headers.get("content-type") or "").lower()
    if content_type and "html" not in content_type and "xml" not in content_type:
        raise JobImportError("El enlace no parece una página web de una vacante.")

    final_url = str(response.url)
    extracted, method = extract_job_from_html(response.text, final_url)
    if not extracted.get("title"):
        raise JobImportError(
            "No se encontró información de la vacante en ese enlace. "
            "Prueba con la URL pública de la oferta."
        )
    if not extracted.get("url"):
        extracted["url"] = final_url
    return extracted, method
