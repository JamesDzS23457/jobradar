import logging
from typing import Any

import httpx

from app.models import Preferences
from app.services.cv_parser import find_skills
from app.services.location import infer_remote_scope, infer_remote_type, seniority_from_title
from app.services.sources.base import JobSource

logger = logging.getLogger(__name__)


class JoobleSource(JobSource):
    name = "jooble"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        roles = [str(role).strip() for role in (prefs.roles or prefs.keywords or ["backend developer"]) if str(role).strip()]
        keywords = ", ".join(roles[:6]) or "backend developer"
        body = {"keywords": keywords, "location": prefs.home_city or "Bogotá"}
        try:
            response = httpx.post(
                f"https://jooble.org/api/{self.api_key}",
                json=body,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Jooble query failed: %s", exc)
            return []

        jobs: list[dict[str, Any]] = []
        for item in payload.get("jobs", []) or []:
            title = item.get("title") or ""
            description = item.get("snippet") or ""
            location = item.get("location") or ""
            remote_type = infer_remote_type({"remote_type": "", "location_text": location, "description": description})
            jobs.append(
                {
                    "source": "jooble",
                    "external_id": str(item.get("id") or ""),
                    "title": title,
                    "company": item.get("company") or item.get("source") or "",
                    "description": description,
                    "location_text": location,
                    "city": location.split(",")[0].strip() if location else "",
                    "country": "Colombia" if "colombia" in location.lower() else "",
                    "remote_type": remote_type,
                    "remote_scope": infer_remote_scope(
                        {"location_text": location, "country": "", "description": description}
                    ),
                    "salary_min": None,
                    "salary_max": None,
                    "currency": "COP",
                    "url": item.get("link") or "",
                    "posted_at": item.get("updated"),
                    "skills_required": find_skills(f"{title} {description}"),
                    "skills_nice": [],
                    "seniority": seniority_from_title(title),
                    "years_experience": 0,
                    "languages": {},
                    "red_flags": [],
                }
            )
        return jobs
