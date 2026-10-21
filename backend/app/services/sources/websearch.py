"""Find public job postings across the web through the Brave Search API.

This connector deliberately reads only public pages that expose structured
job data. It does not bypass logins or scrape private/authenticated portals.
The final URL is preserved so the user applies on the original site.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models import Preferences
from app.services.job_import import (
    JobImportError,
    JobLinkOnlyError,
    import_job_from_url,
    link_only_payload,
)
from app.services.sources.base import JobSource

logger = logging.getLogger(__name__)

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
JOB_HOSTS = {
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "computrabajo.com",
    "elempleo.com",
    "magneto.com.co",
    "getonbrd.com",
    "torre.ai",
    "workana.com",
    "remotive.com",
    "remoteok.com",
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "breezy.hr",
    "teamtailor.com",
}
JOB_PATH_MARKERS = ("/job/", "/jobs/", "/empleo", "/careers/", "/vacante", "/offer", "/position")
MANUAL_HOSTS = {
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "computrabajo.com",
    "elempleo.com",
    "magneto.com.co",
}


class WebSearchSource(JobSource):
    name = "websearch"

    def __init__(self, api_key: str, max_jobs: int = 8) -> None:
        self.api_key = api_key
        self.max_jobs = max_jobs

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        with httpx.Client(timeout=25, headers=headers) as client:
            for index, query in enumerate(self._queries(prefs)):
                if index:
                    # Brave's free plan allows roughly one request per second.
                    time.sleep(1.1)
                try:
                    response = client.get(
                        BRAVE_ENDPOINT,
                        params={
                            "q": query,
                            "count": 10,
                            "country": "CO",
                            "search_lang": "es",
                            "safesearch": "moderate",
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                except Exception as exc:  # pragma: no cover - network dependent
                    logger.warning("Brave web search failed (%s): %s", query, exc)
                    continue

                for item in (payload.get("web") or {}).get("results", []) or []:
                    url = str(item.get("url") or "").strip()
                    if not url or url in seen or not self._looks_like_job(url):
                        continue
                    seen.add(url)
                    try:
                        extracted, _ = import_job_from_url(url)
                    except JobImportError as exc:
                        if isinstance(exc, JobLinkOnlyError) or self._is_manual_host(url):
                            jobs.append(link_only_payload(url, str(exc), collector="websearch"))
                        else:
                            logger.info("Skipping %s: %s", url, exc)
                        if len(jobs) >= self.max_jobs:
                            return jobs
                        continue
                    except Exception:  # pragma: no cover - network dependent
                        logger.exception("Could not import web result %s", url)
                        continue
                    extracted["collector"] = "websearch"
                    jobs.append(extracted)
                    if len(jobs) >= self.max_jobs:
                        return jobs
        return jobs

    def _queries(self, prefs: Preferences) -> list[str]:
        roles = [role.strip() for role in (prefs.roles or []) if role.strip()] or ["backend developer"]
        city = prefs.home_city or "Bogotá"
        country = prefs.country or "Colombia"
        queries: list[str] = []
        for role in roles[:2]:
            queries.append(f'"{role}" "{city}" {country} empleo')
            queries.append(f'site:computrabajo.com.co "{role}" "{city}"')
            queries.append(f'site:elempleo.com "{role}" "{city}"')
        if roles:
            queries.append(f'site:getonbrd.com "{roles[0]}"')
            queries.append(f'site:torre.ai "{roles[0]}"')
        return queries[:6]

    @staticmethod
    def _is_manual_host(url: str) -> bool:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return any(host == item or host.endswith(f".{item}") for item in MANUAL_HOSTS)

    @staticmethod
    def _looks_like_job(url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if any(host == job_host or host.endswith(f".{job_host}") for job_host in JOB_HOSTS):
            return True
        path = parsed.path.lower()
        return any(marker in path for marker in JOB_PATH_MARKERS)
