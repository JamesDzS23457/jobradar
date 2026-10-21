import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.models import Preferences
from app.services.location import infer_remote_scope, infer_remote_type, seniority_from_title
from app.services.sources.base import JobSource

logger = logging.getLogger(__name__)


def _parse_posted_at(item: dict[str, Any]) -> datetime | None:
    raw = item.get("job_posted_at_datetime_utc") or item.get("job_posted_at")
    if raw:
        text = str(raw).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
        normalized = (
            text.lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        now = datetime.now(UTC)
        if "ayer" in normalized or "yesterday" in normalized:
            return now - timedelta(days=1)
        if "hoy" in normalized or normalized in {"today", "just posted"}:
            return now
        match = re.search(r"(?:hace\s+)?(\d+)\s*(minuto|minutos|hora|horas|dia|dias|semana|semanas|mes|meses|minute|minutes|hour|hours|day|days|week|weeks|month|months)", normalized)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit.startswith(("minuto", "minute")):
                return now - timedelta(minutes=amount)
            if unit.startswith(("hora", "hour")):
                return now - timedelta(hours=amount)
            if unit.startswith(("dia", "day")):
                return now - timedelta(days=amount)
            if unit.startswith(("semana", "week")):
                return now - timedelta(weeks=amount)
            if unit.startswith(("mes", "month")):
                return now - timedelta(days=amount * 30)
        if "un mes" in normalized or "a month" in normalized:
            return now - timedelta(days=30)
    timestamp = item.get("job_posted_at_timestamp")
    if isinstance(timestamp, (int, float)) and timestamp > 0:
        seconds = timestamp / 1000 if timestamp > 10_000_000_000 else timestamp
        return datetime.fromtimestamp(seconds, tz=UTC)
    return None


class JSearchSource(JobSource):
    name = "jsearch"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @staticmethod
    def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data") or []
        if isinstance(data, dict):
            data = data.get("jobs") or []
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        roles = [str(role).strip() for role in (prefs.roles or prefs.keywords or ["backend developer"]) if str(role).strip()]
        role_terms = " OR ".join(roles[:2]) or "backend developer"
        location = prefs.home_city or "Bogotá"
        query = (
            f"remote {role_terms} jobs in Colombia"
            if prefs.remote_preference == "remote"
            else f"{role_terms} jobs in {location}, Colombia"
        )
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        jobs: list[dict[str, Any]] = []
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    "https://jsearch.p.rapidapi.com/search-v2",
                    headers=headers,
                    params={
                        "query": query,
                        "page": "1",
                        "num_pages": "1",
                        "date_posted": "month",
                        "country": "co",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("JSearch query failed (%s): %s", query, exc)
            return []

        for item in self._extract_items(payload):
            jobs.append(self._normalize(item))
        return jobs

    def _normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        raw_location = str(item.get("job_location") or "").split("•")[0].strip()
        city = item.get("job_city") or (raw_location.split(",")[0].strip() if raw_location else "")
        country = item.get("job_country") or (
            "Colombia" if "colombia" in raw_location.lower() or "bogot" in raw_location.lower() else ""
        )
        location_text = raw_location or ", ".join(part for part in [city, country] if part) or "Remoto"
        is_remote = bool(item.get("job_is_remote"))
        title = item.get("job_title") or ""
        description = item.get("job_description") or ""
        remote_type = "remote" if is_remote else infer_remote_type(
            {"remote_type": "", "location_text": location_text, "description": description}
        )
        return {
            "source": "jsearch",
            "collector": "jsearch",
            "external_id": item.get("job_id") or "",
            "title": title,
            "company": item.get("employer_name") or "",
            "description": description,
            "location_text": location_text,
            "city": city,
            "country": country,
            "remote_type": remote_type,
            "remote_scope": infer_remote_scope(
                {"location_text": f"{city} {country}", "country": country, "description": description}
            ),
            "salary_min": item.get("job_min_salary"),
            "salary_max": item.get("job_max_salary"),
            "currency": item.get("job_salary_currency") or "USD",
            "url": item.get("job_apply_link") or item.get("job_google_link") or "",
            "posted_at": _parse_posted_at(item),
            "skills_required": item.get("job_required_skills") or [],
            "skills_nice": [],
            "seniority": seniority_from_title(title),
            "years_experience": 0,
            "languages": {},
            "red_flags": [],
        }
