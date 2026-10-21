import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import AlertLog, Job, Match, Preferences, Profile, SearchRun
from app.services.cv_parser import find_skills
from app.services.emailer import send_match_alerts
from app.services.language import infer_job_languages
from app.services.location import infer_remote_scope, infer_remote_type, seniority_from_title
from app.services.matching import canonical_skill, recompute_all
from app.services.sources import get_sources
from app.services.text_clean import clean_html_text, json_safe

logger = logging.getLogger(__name__)

JOB_REFRESH_FIELDS = (
    "title",
    "company",
    "description",
    "location_text",
    "city",
    "country",
    "remote_type",
    "remote_scope",
    "salary_min",
    "salary_max",
    "currency",
    "url",
    "posted_at",
    "raw_json",
    "skills_required",
    "skills_nice",
    "seniority",
    "years_experience",
    "languages",
    "red_flags",
    "link_only",
    "collector",
    "dedupe_key",
)


def _clip(value: Any, limit: int) -> str:
    return str(value or "")[:limit]


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(round(float(str(value).replace(",", ""))))
    except (TypeError, ValueError):
        return None


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text[:10], fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
    return None


TRACKING_PARAMS = {
    "position",
    "pagenum",
    "refid",
    "trackingid",
    "trk",
    "fgoa",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
}


def canonical_url(raw_url: str) -> str:
    text = (raw_url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return text.lower()
    host = parsed.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith("utm_")
    ]
    return urlunparse(("https", host, path, "", urlencode(sorted(query)), ""))


def dedupe_key_for(data: dict[str, Any]) -> str:
    canonical = canonical_url(str(data.get("url") or ""))
    if canonical:
        return hashlib.sha256(f"url:{canonical}".encode()).hexdigest()
    parts = [
        str(data.get("title") or "").strip().lower(),
        str(data.get("company") or "").strip().lower(),
        str(data.get("location_text") or "").strip().lower(),
    ]
    return hashlib.sha256("text:" + "|".join(parts).encode("utf-8")).hexdigest()


def job_hash(data: dict[str, Any]) -> str:
    key = "|".join(
        [
            str(data.get("source") or ""),
            str(data.get("external_id") or ""),
            str(data.get("title") or "").strip().lower(),
            str(data.get("company") or "").strip().lower(),
            str(data.get("location_text") or "").strip().lower(),
            str(data.get("url") or "").strip().lower(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def normalize_job_data(data: dict[str, Any]) -> dict[str, Any]:
    title = clean_html_text(data.get("title") or "", max_length=240)
    description = clean_html_text(data.get("description") or "", max_length=50_000)
    location_text = clean_html_text(data.get("location_text") or "", max_length=240)
    country = clean_html_text(data.get("country") or "", max_length=120)
    city = clean_html_text(data.get("city") or "", max_length=120)
    remote_type = infer_remote_type(
        {
            "remote_type": data.get("remote_type"),
            "location_text": location_text,
            "description": description,
        }
    )
    remote_scope = infer_remote_scope(
        {
            "remote_scope": data.get("remote_scope"),
            "location_text": location_text,
            "country": country,
            "description": description,
        }
    )
    skills = list(
        dict.fromkeys(canonical_skill(skill) for skill in (data.get("skills_required") or []) if str(skill).strip())
    )
    if not skills:
        skills = find_skills(f"{title} {description}")[:10]
    nice = list(
        dict.fromkeys(canonical_skill(skill) for skill in (data.get("skills_nice") or []) if str(skill).strip())
    )
    languages = data.get("languages") or {}
    if not languages:
        languages = infer_job_languages(f"{title}\n{description}")
    normalized = {
        "source": _clip(data.get("source") or "unknown", 50),
        "external_id": _clip(data.get("external_id") or "", 200),
        "title": _clip(title, 240),
        "company": _clip(str(data.get("company") or "").strip(), 160),
        "description": description[:50_000],
        "location_text": _clip(
            location_text or ("Remoto" if remote_type == "remote" else ""), 240
        ),
        "city": _clip(city, 120),
        "country": _clip(country or ("Worldwide" if remote_type == "remote" else ""), 120),
        "remote_type": remote_type,
        "remote_scope": remote_scope,
        "salary_min": _int_or_none(data.get("salary_min")),
        "salary_max": _int_or_none(data.get("salary_max")),
        "currency": _clip(str(data.get("currency") or "COP").upper(), 10),
        "url": _clip(data.get("url") or "", 700),
        "posted_at": parse_datetime(data.get("posted_at")),
        "skills_required": skills,
        "skills_nice": nice,
        "seniority": data.get("seniority") or seniority_from_title(title),
        "years_experience": int(data.get("years_experience") or 0),
        "languages": languages,
        "red_flags": data.get("red_flags") or [],
        "raw_json": json_safe(data),
        "link_only": bool(data.get("link_only")),
        "collector": _clip(data.get("collector") or data.get("source") or "", 50),
    }
    normalized["hash"] = job_hash(normalized)
    normalized["dedupe_key"] = dedupe_key_for(normalized)
    return normalized


def upsert_job(db: Session, data: dict[str, Any], refresh: bool = False) -> tuple[Job, bool]:
    existing = db.scalar(select(Job).where(Job.hash == data["hash"]))
    if existing is None and data.get("dedupe_key"):
        existing = db.scalar(
            select(Job)
            .where(Job.dedupe_key == data["dedupe_key"])
            .order_by(Job.id)
        )
    now = datetime.now(UTC)
    if existing:
        existing.last_seen_at = now
        existing.fetched_at = now
        existing.status = existing.status or "new"
        if refresh:
            for field in JOB_REFRESH_FIELDS:
                if field in data:
                    setattr(existing, field, data[field])
        return existing, False
    job = Job(
        source=data["source"],
        external_id=data["external_id"],
        title=data["title"],
        company=data["company"],
        description=data["description"],
        location_text=data["location_text"],
        city=data["city"],
        country=data["country"],
        remote_type=data["remote_type"],
        remote_scope=data["remote_scope"],
        salary_min=data["salary_min"],
        salary_max=data["salary_max"],
        currency=data["currency"],
        url=data["url"],
        posted_at=data["posted_at"],
        fetched_at=now,
        last_seen_at=now,
        hash=data["hash"],
        dedupe_key=data.get("dedupe_key") or "",
        raw_json=data["raw_json"],
        skills_required=data["skills_required"],
        skills_nice=data["skills_nice"],
        seniority=data["seniority"],
        years_experience=data["years_experience"],
        languages=data["languages"],
        red_flags=data["red_flags"],
        link_only=data.get("link_only", False),
        collector=data.get("collector") or data.get("source") or "",
    )
    db.add(job)
    db.flush()
    return job, True


def run_search(db: Session, profile: Profile, prefs: Preferences, settings: Settings) -> SearchRun:
    run = SearchRun(started_at=datetime.now(UTC), sources={}, errors=[])
    db.add(run)
    db.commit()
    db.refresh(run)

    found = 0
    new = 0
    sources_summary: dict[str, Any] = {}
    errors: list[str] = []

    for source in get_sources(settings):
        try:
            items = source.fetch(prefs)
            sources_summary[source.name] = len(items)
            for item in items:
                normalized = normalize_job_data(item)
                _, is_new = upsert_job(db, normalized)
                found += 1
                new += 1 if is_new else 0
            db.commit()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.exception("Source %s failed", source.name)
            summary = str(exc).splitlines()[0][:300] if str(exc) else exc.__class__.__name__
            errors.append(f"{source.name}: {summary}")
            db.rollback()

    recompute_all(db, profile, prefs)

    if settings.smtp_configured and not settings.demo_mode:
        try:
            send_match_alerts(db, settings)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.exception("Alert sending failed")
            errors.append(f"email: {exc}")

    run.finished_at = datetime.now(UTC)
    run.found = found
    run.new = new
    run.sources = sources_summary
    run.errors = errors
    db.commit()
    db.refresh(run)
    return run


def latest_search_run(db: Session) -> SearchRun | None:
    return db.scalar(select(SearchRun).order_by(SearchRun.started_at.desc()).limit(1))


def eligible_top_matches(db: Session, limit: int = 5) -> list[Match]:
    return list(
        db.scalars(
            select(Match)
            .where(Match.eligible.is_(True))
            .order_by(Match.score.desc())
            .limit(limit)
        ).all()
    )


def mark_alert_sent(db: Session, job_id: int, match_id: int | None, status: str, error: str = "") -> None:
    db.add(AlertLog(job_id=job_id, match_id=match_id, status=status, error=error))
    db.commit()


LEGACY_SEARCH_ERROR_MARKERS = (
    "Object of type datetime is not JSON serializable",
)


def clear_legacy_search_errors(db: Session) -> int:
    """Remove obsolete errors from runs created before the JSearch date fix."""
    runs = list(db.scalars(select(SearchRun)).all())
    changed = 0
    for run in runs:
        errors = list(run.errors or [])
        filtered = [
            error
            for error in errors
            if not any(marker in str(error) for marker in LEGACY_SEARCH_ERROR_MARKERS)
        ]
        if len(filtered) != len(errors):
            run.errors = filtered
            changed += 1
    if changed:
        db.commit()
    return changed


def backfill_dedupe_keys(db: Session) -> int:
    changed = 0
    for job in db.scalars(select(Job)).all():
        if not job.dedupe_key:
            job.dedupe_key = dedupe_key_for(
                {
                    "url": job.url,
                    "title": job.title,
                    "company": job.company,
                    "location_text": job.location_text,
                }
            )
            changed += 1
    if changed:
        db.commit()
    return changed


def discard_duplicate_jobs(db: Session) -> int:
    """Keep the most useful record for each canonical URL and hide the rest."""
    jobs = list(db.scalars(select(Job).order_by(Job.id)).all())
    groups: dict[str, list[Job]] = {}
    for job in jobs:
        key = job.dedupe_key or dedupe_key_for(
            {
                "url": job.url,
                "title": job.title,
                "company": job.company,
                "location_text": job.location_text,
            }
        )
        if key:
            groups.setdefault(key, []).append(job)

    discarded = 0
    for group in groups.values():
        active = [job for job in group if job.status != "discarded"]
        if len(active) < 2:
            continue

        def priority(job: Job) -> tuple[int, int]:
            application = job.application
            if application is not None and application.status in {"applied", "interview", "offer"}:
                return (0, job.id)
            if application is not None and application.status == "saved":
                return (1, job.id)
            return (2, job.id)

        keeper = min(active, key=priority)
        for job in active:
            if job.id == keeper.id:
                continue
            job.status = "discarded"
            raw = dict(job.raw_json or {})
            raw["dedupe_of"] = keeper.id
            job.raw_json = raw
            discarded += 1
    if discarded:
        db.commit()
    return discarded
