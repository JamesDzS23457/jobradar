import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import AlertLog, Job, Match, Preferences, Profile, SearchRun
from app.services.cv_parser import find_skills
from app.services.emailer import send_match_alerts
from app.services.location import infer_remote_scope, infer_remote_type, seniority_from_title
from app.services.matching import canonical_skill, recompute_all
from app.services.sources import get_sources

logger = logging.getLogger(__name__)


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
    title = str(data.get("title") or "").strip()
    description = str(data.get("description") or "").strip()
    location_text = str(data.get("location_text") or "").strip()
    country = str(data.get("country") or "").strip()
    city = str(data.get("city") or "").strip()
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
    if not languages and any(word in description.lower() for word in ("english", "inglés", "ingles")):
        languages = {"Inglés": "B2"}
    normalized = {
        "source": str(data.get("source") or "unknown"),
        "external_id": str(data.get("external_id") or ""),
        "title": title,
        "company": str(data.get("company") or "").strip(),
        "description": description,
        "location_text": location_text or ("Remoto" if remote_type == "remote" else ""),
        "city": city,
        "country": country or ("Worldwide" if remote_type == "remote" else ""),
        "remote_type": remote_type,
        "remote_scope": remote_scope,
        "salary_min": data.get("salary_min"),
        "salary_max": data.get("salary_max"),
        "currency": str(data.get("currency") or "COP"),
        "url": str(data.get("url") or ""),
        "posted_at": parse_datetime(data.get("posted_at")),
        "skills_required": skills,
        "skills_nice": nice,
        "seniority": data.get("seniority") or seniority_from_title(title),
        "years_experience": int(data.get("years_experience") or 0),
        "languages": languages,
        "red_flags": data.get("red_flags") or [],
        "raw_json": data,
    }
    normalized["hash"] = job_hash(normalized)
    return normalized


def upsert_job(db: Session, data: dict[str, Any]) -> tuple[Job, bool]:
    existing = db.scalar(select(Job).where(Job.hash == data["hash"]))
    now = datetime.now(UTC)
    if existing:
        existing.last_seen_at = now
        existing.status = existing.status or "new"
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
        raw_json=data["raw_json"],
        skills_required=data["skills_required"],
        skills_nice=data["skills_nice"],
        seniority=data["seniority"],
        years_experience=data["years_experience"],
        languages=data["languages"],
        red_flags=data["red_flags"],
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
            errors.append(f"{source.name}: {exc}")
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
