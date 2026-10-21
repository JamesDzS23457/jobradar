"""Discover current public Computrabajo listings without logging in.

Only the public search results page is read. Job detail pages are linked, not
bypassed; the user opens the original portal to apply.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.models import Preferences
from app.services.cv_parser import find_skills
from app.services.location import infer_remote_scope, infer_remote_type, seniority_from_title
from app.services.sources.base import JobSource
from app.services.sources.jsearch import _parse_posted_at

logger = logging.getLogger(__name__)

BASE_URL = "https://www.computrabajo.com.co"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 JobRadar/0.1"
)


EXCLUDED_TITLE_MARKERS = (
    "comercial",
    "ventas",
    "negocio",
    "cuenta",
    "canal",
    "trade",
    "ejecutiv",
    "moto propia",
    "mercadeo",
    "marketing",
    "publicidad",
    "mercado",
    "distribuidor",
    "vendedor",
    "ruta",
    "monitoreo",
    "trafico",
    "tráfico",
    "gps",
)
TECH_TITLE_MARKERS = (
    "desarrollador",
    "developer",
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    "software",
    "programador",
    "ingenier",
    "data",
    "datos",
    "devops",
    "qa",
    "analista",
    "python",
    "java",
    "react",
    "node",
    "sql",
    "diseñador",
    "designer",
)


def _is_relevant_title(title: str) -> bool:
    normalized = title.lower()
    if any(marker in normalized for marker in EXCLUDED_TITLE_MARKERS):
        return False
    return any(marker in normalized for marker in TECH_TITLE_MARKERS)


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = normalized.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "backend-developer"


class ComputrabajoSource(JobSource):
    name = "computrabajo"

    def __init__(self, max_jobs: int = 20) -> None:
        self.max_jobs = max_jobs

    @staticmethod
    def _parse_articles(html: str, page_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[dict[str, Any]] = []
        for article in soup.select("article.box_offer"):
            link = article.select_one("h2 a[href]")
            if link is None:
                continue
            title = link.get_text(" ", strip=True)
            href = str(link.get("href") or "").split("#")[0]
            if not title or not href or not _is_relevant_title(title):
                continue
            url = urljoin(page_url, href)
            company_node = article.select_one("a[offer-grid-article-company-url]")
            company = company_node.get_text(" ", strip=True) if company_node else ""
            location_nodes = article.select("p.fs16.fc_base.mt5")
            location = ""
            if len(location_nodes) >= 2:
                location = location_nodes[1].get_text(" ", strip=True)
            elif location_nodes:
                location = location_nodes[-1].get_text(" ", strip=True)
            date_node = article.select_one("p.fs13.fc_aux")
            date_text = date_node.get_text(" ", strip=True) if date_node else ""
            remote_type = infer_remote_type(
                {"remote_type": "", "location_text": location, "description": title}
            )
            jobs.append(
                {
                    "source": "computrabajo",
                    "collector": "computrabajo",
                    "external_id": str(article.get("data-id") or url),
                    "title": title,
                    "company": company,
                    "description": (
                        "Oferta publicada en Computrabajo. Abre el enlace original para ver "
                        "la descripción completa y postularte en el portal."
                    ),
                    "location_text": location or "Colombia",
                    "city": location.split(",")[0].strip() if location else "",
                    "country": "Colombia",
                    "remote_type": remote_type,
                    "remote_scope": infer_remote_scope(
                        {"location_text": location, "country": "Colombia", "description": title}
                    ),
                    "salary_min": None,
                    "salary_max": None,
                    "currency": "COP",
                    "url": url,
                    "posted_at": _parse_posted_at({"job_posted_at": date_text}),
                    "skills_required": find_skills(title),
                    "skills_nice": [],
                    "seniority": seniority_from_title(title),
                    "years_experience": 0,
                    "languages": {},
                    "red_flags": ["Requiere iniciar sesión en Computrabajo para postularte"],
                    "requires_login": True,
                    "access_note": (
                        "Abre el enlace original en Computrabajo para ver la oferta completa; "
                        "el portal puede pedir iniciar sesión para postularte."
                    ),
                }
            )
            if len(jobs) >= 20:
                break
        return jobs

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        roles = [role.strip() for role in (prefs.roles or []) if role.strip()] or ["backend developer"]
        city = (prefs.home_city or "Bogotá").split(",")[0].strip()
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "es-CO,es;q=0.9"}
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        role_slugs = list(dict.fromkeys(_slug(role) for role in roles[:2]))
        search_urls = [f"{BASE_URL}/trabajo-de-{slug}-en-{_slug(city)}" for slug in role_slugs]
        generic_url = f"{BASE_URL}/trabajo-de-desarrollador-en-{_slug(city)}"
        if generic_url not in search_urls:
            search_urls.append(generic_url)
        with httpx.Client(timeout=25, headers=headers, follow_redirects=True) as client:
            for url in search_urls:
                try:
                    response = client.get(url)
                    response.raise_for_status()
                except Exception as exc:  # pragma: no cover - network dependent
                    logger.warning("Computrabajo search failed (%s): %s", url, exc)
                    continue
                for item in self._parse_articles(response.text, str(response.url)):
                    if item["url"] in seen:
                        continue
                    seen.add(item["url"])
                    jobs.append(item)
                    if len(jobs) >= self.max_jobs:
                        return jobs
        return jobs
