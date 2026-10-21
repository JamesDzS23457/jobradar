import logging
from typing import Any

import httpx

from app.models import Preferences
from app.services.location import infer_remote_scope, seniority_from_title
from app.services.sources.base import JobSource

logger = logging.getLogger(__name__)


class RemotiveSource(JobSource):
    name = "remotive"

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        try:
            response = httpx.get("https://remotive.com/api/remote-jobs", params={"limit": 40}, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Remotive query failed: %s", exc)
            return []

        jobs: list[dict[str, Any]] = []
        for item in payload.get("jobs", []) or []:
            title = item.get("title") or ""
            location = item.get("candidate_required_location") or "Worldwide"
            description = item.get("description") or ""
            jobs.append(
                {
                    "source": "remotive",
                    "external_id": str(item.get("id") or ""),
                    "title": title,
                    "company": item.get("company_name") or "",
                    "description": description,
                    "location_text": f"Remote - {location}",
                    "city": "",
                    "country": location,
                    "remote_type": "remote",
                    "remote_scope": infer_remote_scope(
                        {"location_text": location, "country": location, "description": description}
                    ),
                    "salary_min": None,
                    "salary_max": None,
                    "currency": "USD",
                    "url": item.get("url") or "",
                    "posted_at": item.get("publication_date"),
                    "skills_required": item.get("tags") or [],
                    "skills_nice": [],
                    "seniority": seniority_from_title(title),
                    "years_experience": 0,
                    "languages": {},
                    "red_flags": [],
                }
            )
        return jobs
