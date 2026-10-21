import logging
from typing import Any

import httpx

from app.models import Preferences
from app.services.location import infer_remote_scope, seniority_from_title
from app.services.sources.base import JobSource

logger = logging.getLogger(__name__)


class JSearchSource(JobSource):
    name = "jsearch"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        roles = prefs.roles or ["backend developer"]
        location = prefs.home_city or "Bogotá"
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        jobs: list[dict[str, Any]] = []
        queries = [f"{role} jobs in {location}, Colombia" for role in roles[:2]]
        queries.append(f"remote {roles[0]} jobs in Colombia")
        with httpx.Client(timeout=30) as client:
            for query in queries:
                try:
                    response = client.get(
                        "https://jsearch.p.rapidapi.com/search",
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
                    continue
                for item in payload.get("data", []) or []:
                    jobs.append(self._normalize(item))
        return jobs

    def _normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        city = item.get("job_city") or ""
        country = item.get("job_country") or ""
        is_remote = bool(item.get("job_is_remote"))
        title = item.get("job_title") or ""
        description = item.get("job_description") or ""
        remote_type = "remote" if is_remote else "unknown"
        payload = {
            "source": "jsearch",
            "external_id": item.get("job_id") or "",
            "title": title,
            "company": item.get("employer_name") or "",
            "description": description,
            "location_text": ", ".join(part for part in [city, country] if part) or "Remoto",
            "city": city,
            "country": country or ("Worldwide" if is_remote else ""),
            "remote_type": remote_type,
            "remote_scope": infer_remote_scope(
                {"location_text": f"{city} {country}", "country": country, "description": description}
            ),
            "salary_min": item.get("job_min_salary"),
            "salary_max": item.get("job_max_salary"),
            "currency": item.get("job_salary_currency") or "USD",
            "url": item.get("job_apply_link") or "",
            "posted_at": item.get("job_posted_at_datetime_utc"),
            "skills_required": item.get("job_required_skills") or [],
            "skills_nice": [],
            "seniority": seniority_from_title(title),
            "years_experience": 0,
            "languages": {},
            "red_flags": [],
        }
        return payload
