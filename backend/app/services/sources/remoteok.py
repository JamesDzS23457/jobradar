import logging
from typing import Any

import httpx

from app.models import Preferences
from app.services.location import infer_remote_scope, seniority_from_title
from app.services.sources.base import JobSource

logger = logging.getLogger(__name__)


class RemoteOKSource(JobSource):
    name = "remoteok"

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        try:
            response = httpx.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "JobRadar/0.1 (personal job search assistant)"},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("RemoteOK query failed: %s", exc)
            return []

        jobs: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict) or "id" not in item:
                continue
            title = item.get("position") or item.get("title") or ""
            location = item.get("location") or "Worldwide"
            description = item.get("description") or ""
            jobs.append(
                {
                    "source": "remoteok",
                    "external_id": str(item.get("id") or ""),
                    "title": title,
                    "company": item.get("company") or "",
                    "description": description,
                    "location_text": f"Remote - {location}",
                    "city": "",
                    "country": location,
                    "remote_type": "remote",
                    "remote_scope": infer_remote_scope(
                        {"location_text": location, "country": location, "description": description}
                    ),
                    "salary_min": item.get("salary_min") or None,
                    "salary_max": item.get("salary_max") or None,
                    "currency": "USD",
                    "url": item.get("url") or item.get("apply_url") or "",
                    "posted_at": item.get("date"),
                    "skills_required": item.get("tags") or [],
                    "skills_nice": [],
                    "seniority": seniority_from_title(title),
                    "years_experience": 0,
                    "languages": {},
                    "red_flags": [],
                }
            )
        return jobs
