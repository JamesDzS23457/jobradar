import re
from typing import Any

from app.models import Job, Preferences

COLOMBIA_ALIASES = {"colombia", "co", "bogota", "bogotá", "medellin", "medellín", "cali", "barranquilla"}
LATAM_ALIASES = {
    "latin america",
    "latam",
    "latinoamerica",
    "latinoamérica",
    "south america",
    "sudamerica",
    "sudamérica",
    "mexico",
    "méxico",
    "argentina",
    "chile",
    "peru",
    "perú",
    "ecuador",
    "uruguay",
    "paraguay",
    "bolivia",
    "venezuela",
    "costa rica",
    "panama",
    "panamá",
    "dominican republic",
    "república dominicana",
}
GLOBAL_ALIASES = {"worldwide", "global", "anywhere", "remote", "remoto", "world"}
US_ONLY_ALIASES = {"united states", "usa", "us only", "canada", "north america", "ee. uu.", "estados unidos"}

REMOTE_TYPES = {"remote", "hybrid", "onsite", "unknown"}
REMOTE_SCOPES = {"colombia", "latam", "global", "us_only", "national", "unknown"}


def norm(value: str | None) -> str:
    return (value or "").strip().lower()


def infer_remote_type(job: Job | dict[str, Any]) -> str:
    remote_type = norm(job.get("remote_type") if isinstance(job, dict) else job.remote_type)
    if remote_type in REMOTE_TYPES:
        return remote_type
    text = norm(
        (job.get("location_text") if isinstance(job, dict) else job.location_text)
        or ""
    ) + " " + norm((job.get("description") if isinstance(job, dict) else job.description) or "")
    if any(word in text for word in ("hybrid", "híbrido", "hibrido", "mixto")):
        return "hybrid"
    if any(word in text for word in ("remote", "remoto", "teletrabajo", "work from home")):
        return "remote"
    if any(word in text for word in ("on-site", "onsite", "presencial")):
        return "onsite"
    return "unknown"


def infer_remote_scope(job: Job | dict[str, Any]) -> str:
    scope = norm(job.get("remote_scope") if isinstance(job, dict) else job.remote_scope)
    if scope in REMOTE_SCOPES:
        return scope
    text = norm(
        " ".join(
            [
                str(job.get("location_text") if isinstance(job, dict) else job.location_text or ""),
                str(job.get("country") if isinstance(job, dict) else job.country or ""),
                str(job.get("description") if isinstance(job, dict) else job.description or ""),
            ]
        )
    )
    if any(alias in text for alias in US_ONLY_ALIASES):
        return "us_only"
    if "colombia" in text:
        return "colombia"
    if any(alias in text for alias in LATAM_ALIASES):
        return "latam"
    if any(alias in text for alias in GLOBAL_ALIASES):
        return "global"
    return "unknown"


def _contains_any(text: str, values: set[str]) -> bool:
    return any(value in text for value in values)


def location_fit(job: Job | dict[str, Any], prefs: Preferences) -> tuple[float, bool, str]:
    remote_type = infer_remote_type(job)
    remote_scope = infer_remote_scope(job)
    raw_city = (job.get("city") if isinstance(job, dict) else job.city) or ""
    city = norm(raw_city)
    country = norm(job.get("country") if isinstance(job, dict) else job.country)
    location_text = norm(job.get("location_text") if isinstance(job, dict) else job.location_text)
    home_city = norm(prefs.home_city)
    commute = {norm(city_name) for city_name in (prefs.commute_cities or [])}
    display_city = raw_city or location_text.split(",")[0].strip()

    if remote_type == "remote":
        if remote_scope == "us_only" or _contains_any(country, US_ONLY_ALIASES):
            return 0.0, False, "Remoto limitado a Estados Unidos/Canadá"
        if country == "colombia" or remote_scope == "colombia" or "colombia" in location_text:
            return 9.0, True, "Remoto en Colombia"
        if remote_scope == "latam" or _contains_any(country, LATAM_ALIASES):
            return (8.0, True, "Remoto en Latinoamérica") if prefs.accept_international_remote else (
                0.0,
                False,
                "Remoto internacional desactivado",
            )
        if remote_scope == "global" or _contains_any(country, GLOBAL_ALIASES):
            return (7.0, True, "Remoto global") if prefs.accept_international_remote else (
                0.0,
                False,
                "Remoto internacional desactivado",
            )
        return 0.0, False, "Ubicación remota no compatible"

    if country == "colombia" or _contains_any(location_text, COLOMBIA_ALIASES):
        if (city and (city == home_city or home_city in city or city in home_city)) or (
            not city and home_city in location_text
        ):
            label = "Híbrido en Bogotá" if remote_type == "hybrid" else "Presencial en Bogotá"
            return 10.0, True, label
        if (city and city in commute) or (not city and any(place in location_text for place in commute)):
            label = "Híbrido en ciudad cercana" if remote_type == "hybrid" else "Presencial en ciudad cercana"
            return 9.0, True, label
        if prefs.accept_relocation:
            return 4.0, True, "Requiere reubicación dentro de Colombia"
        return 0.0, False, f"Presencial/híbrido en {display_city or 'otra ciudad'} (no reubicación)"

    if remote_type == "unknown":
        if country == "colombia" or _contains_any(location_text, COLOMBIA_ALIASES):
            return 5.0, True, "Modalidad no confirmada"
        return 0.0, False, "Ubicación o modalidad no confirmada"

    return 0.0, False, "Presencial/híbrido fuera de Colombia"


def location_label(job: Job) -> str:
    if job.remote_type == "remote":
        return "Remoto"
    if job.remote_type == "hybrid":
        return "Híbrido"
    if job.remote_type == "onsite":
        return "Presencial"
    return "No definido"


def city_matches(text: str, cities: list[str]) -> bool:
    normalized = norm(text)
    return any(norm(city) in normalized for city in cities)


def seniority_from_title(title: str) -> str:
    normalized = norm(title)
    if re.search(r"\b(lead|principal|staff|head)\b", normalized):
        return "lead"
    if re.search(r"\b(senior|sr)\b", normalized):
        return "senior"
    if re.search(r"\b(junior|jr|trainee|intern)\b", normalized):
        return "junior"
    return "mid"
