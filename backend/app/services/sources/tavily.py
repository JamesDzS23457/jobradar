"""Discover public job links through Tavily without requiring a key."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.models import Preferences
from app.services.job_import import (
    JobImportError,
    JobLinkOnlyError,
    import_job_from_url,
    link_only_payload,
)
from app.services.sources.websearch import WebSearchSource

logger = logging.getLogger(__name__)

TAVILY_ENDPOINT = "https://api.tavily.com/search"


class TavilySearchSource(WebSearchSource):
    name = "tavily"

    def __init__(self, api_key: str = "", keyless: bool = True, max_jobs: int = 10) -> None:
        self.api_key = api_key.strip()
        self.keyless = keyless
        self.max_jobs = max_jobs

    @staticmethod
    def _result_urls(payload: dict[str, Any]) -> list[str]:
        urls: list[str] = []
        for item in payload.get("results", []) or []:
            if isinstance(item, dict):
                url = str(item.get("url") or "").strip()
                if url:
                    urls.append(url)
        return urls

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers["X-Tavily-Access-Mode"] = "keyless"

        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        with httpx.Client(timeout=30, headers=headers) as client:
            for index, query in enumerate(self._queries(prefs)):
                if index:
                    time.sleep(1.0)
                try:
                    response = client.post(
                        TAVILY_ENDPOINT,
                        json={
                            "query": query,
                            "max_results": 15,
                            "search_depth": "basic",
                            "include_answer": False,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                except Exception as exc:  # pragma: no cover - network dependent
                    logger.warning("Tavily search failed (%s): %s", query, exc)
                    continue

                for url in self._result_urls(payload):
                    if url in seen or not self._looks_like_job(url):
                        continue
                    seen.add(url)
                    try:
                        extracted, _ = import_job_from_url(url)
                    except JobImportError as exc:
                        if "computrabajo.com" in url.lower():
                            logger.info("Skipping unavailable Computrabajo detail %s", url)
                            continue
                        if isinstance(exc, JobLinkOnlyError) or self._is_manual_host(url):
                            jobs.append(
                                link_only_payload(url, str(exc), collector="tavily")
                            )
                        else:
                            logger.info("Skipping Tavily result %s: %s", url, exc)
                        if len(jobs) >= self.max_jobs:
                            return jobs
                        continue
                    except Exception:  # pragma: no cover - network dependent
                        logger.exception("Could not import Tavily result %s", url)
                        continue
                    final_url = str(extracted.get("url") or url)
                    if not self._looks_like_job(final_url):
                        logger.info("Skipping redirected listing page %s", final_url)
                        continue
                    extracted["collector"] = "tavily"
                    jobs.append(extracted)
                    if len(jobs) >= self.max_jobs:
                        return jobs
        return jobs
