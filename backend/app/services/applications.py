"""Application assistant service.

The assistant prepares structured application data and attachments. The actual
browser interaction is done by the optional local Chrome extension, so the
backend never needs to store portal passwords or bypass CAPTCHAs.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models import (
    Application,
    ApplicationRun,
    ApplicationRunItem,
    ApplicationSession,
    Job,
    Preferences,
    Profile,
    TailoredCV,
)
from app.services.llm import llm_service
from app.services.matching import match_to_dict
from app.services.portals import classify_portal
from app.services.tailoring import export_pdf, fallback_tailored, generate_tailored
from app.services.text_clean import clean_html_text

logger = logging.getLogger(__name__)

SENSITIVE_MARKERS = (
    "salario",
    "salary",
    "pretensión",
    "pretension",
    "autorización",
    "autorizacion",
    "work authorization",
    "sponsorship",
    "visa",
    "discapacidad",
    "disability",
    "veteran",
    "veterano",
    "género",
    "genero",
    "gender",
    "etnia",
    "race",
    "ethnicity",
    "fecha de nacimiento",
    "date of birth",
    "ssn",
    "cédula",
    "cedula",
    "pasaporte",
    "passport",
    "cuenta bancaria",
    "bank account",
)


def resolve_cv_source(value: str | None, prefs: Preferences | None = None) -> str:
    candidate = (value or (prefs.default_cv_source if prefs else "tailored") or "tailored").lower()
    return "original" if candidate == "original" else "tailored"


def original_cv_path(profile: Profile | None) -> Path | None:
    if profile is None or not profile.cv_file_path:
        return None
    path = Path(profile.cv_file_path)
    return path if path.exists() and path.is_file() else None


def _latest_tailored(db: Session, job_id: int) -> TailoredCV | None:
    return db.scalar(
        select(TailoredCV)
        .where(TailoredCV.job_id == job_id)
        .order_by(TailoredCV.created_at.desc())
        .limit(1)
    )


def _tailored_or_generate(
    db: Session,
    job: Job,
    profile: Profile,
    settings: Settings,
) -> TailoredCV:
    tailored = _latest_tailored(db, job.id)
    if tailored is not None:
        return tailored
    return generate_tailored(db, job, profile, job.match, settings)


def _cv_attachment(
    db: Session,
    job: Job,
    profile: Profile,
    settings: Settings,
    cv_source: str,
) -> tuple[str, str, str, TailoredCV | None]:
    if cv_source == "original":
        path = original_cv_path(profile)
        if path is None:
            raise ValueError("No hay un CV original disponible. Sube tu PDF en el perfil.")
        return "original", path.name, str(path), None

    tailored = _tailored_or_generate(db, job, profile, settings)
    path = Path(tailored.pdf_path) if tailored.pdf_path else Path("")
    if not path.exists():
        path = export_pdf(tailored, profile, settings)
        tailored.pdf_path = str(path)
        db.commit()
    return "tailored", path.name, str(path), tailored


def _split_name(name: str) -> tuple[str, str]:
    parts = [part for part in (name or "").strip().split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def build_standard_fields(
    profile: Profile,
    prefs: Preferences,
    tailored: TailoredCV | None,
) -> dict[str, str]:
    first_name, last_name = _split_name(profile.name)
    links = profile.links or {}
    content = tailored.content if tailored else {}
    return {
        "full_name": profile.name or "",
        "first_name": first_name,
        "last_name": last_name,
        "email": profile.email or "",
        "phone": profile.phone or "",
        "location": profile.location or "",
        "city": prefs.home_city or "",
        "country": prefs.country or "",
        "linkedin": links.get("LinkedIn", ""),
        "github": links.get("GitHub", ""),
        "portfolio": links.get("Portafolio", links.get("Portfolio", "")),
        "website": links.get("Portafolio", links.get("Website", "")),
        "current_title": profile.headline or "",
        "current_company": (profile.experience or [{}])[0].get("company", "") if profile.experience else "",
        "years_experience": str(profile.years_experience or ""),
        "salary_expectation": str(prefs.salary_min or ""),
        "salary_currency": prefs.currency or "COP",
        "cover_letter": str(content.get("cover_letter", "")),
    }


def _portal_payload(job: Job, settings: Settings | None = None) -> dict[str, object]:
    portal = classify_portal(job.url, settings).as_dict()
    if job.link_only:
        note = str((job.raw_json or {}).get("access_note") or "")
        portal.update(
            {
                "mode": "manual_only",
                "can_assist": False,
                "can_auto_submit": False,
                "reason": note or "El enlace requiere iniciar sesión en el portal.",
            }
        )
    return portal


def build_preview(
    db: Session,
    job: Job,
    profile: Profile,
    prefs: Preferences,
    settings: Settings,
    cv_source: str | None = None,
) -> dict[str, Any]:
    portal = _portal_payload(job, settings)
    portal_mode = str(portal["mode"])
    source = resolve_cv_source(cv_source, prefs)
    original = original_cv_path(profile)
    tailored = _latest_tailored(db, job.id)
    content = tailored.content if tailored else fallback_tailored(profile, job, job.match)
    warnings: list[str] = []
    if source == "original" and original is None:
        warnings.append("No hay un CV original disponible; se usará el CV adaptado.")
    if source == "original" and original is not None and original.suffix.lower() != ".pdf":
        warnings.append(
            "Tu CV original no es PDF. Si el portal solo acepta PDF, elige el CV adaptado o sube una versión PDF."
        )
    if source == "tailored" and tailored is None:
        warnings.append("El CV adaptado se generará al preparar la postulación.")
    if tailored and not tailored.approved:
        warnings.append("El CV adaptado aún no está aprobado. Revísalo antes de enviarlo.")
    if portal_mode == "manual_only":
        warnings.append(str(portal["reason"]))
    return {
        "job": job_summary(job, include_description=True),
        "portal": portal,
        "cv_source": source,
        "cv_options": {
            "tailored": {
                "available": tailored is not None,
                "file_name": Path(tailored.pdf_path).name if tailored and tailored.pdf_path else "",
                "approved": bool(tailored and tailored.approved),
                "download_url": f"/api/tailored/{tailored.id}/download?format=pdf" if tailored else "",
            },
            "original": {
                "available": original is not None,
                "file_name": original.name if original else "",
                "download_url": "/api/cv/original" if original else "",
            },
        },
        "fields": build_standard_fields(profile, prefs, tailored),
        "cover_letter": str(content.get("cover_letter", "")),
        "warnings": warnings,
        "can_assist": bool(portal["can_assist"]),
        "can_auto_submit": bool(portal["can_auto_submit"]),
    }


def create_session(
    db: Session,
    job: Job,
    profile: Profile,
    prefs: Preferences,
    settings: Settings,
    cv_source: str | None = None,
    run_id: int | None = None,
    status: str = "awaiting_review",
) -> ApplicationSession:
    portal = classify_portal(job.url, settings)
    if job.link_only:
        raise ValueError("Este enlace requiere iniciar sesión en el portal; ábrelo para postularte.")
    if not portal.can_assist:
        raise ValueError(portal.reason)
    source = resolve_cv_source(cv_source, prefs)
    try:
        source, file_name, path, tailored = _cv_attachment(db, job, profile, settings, source)
    except ValueError:
        if source == "original":
            source, file_name, path, tailored = _cv_attachment(db, job, profile, settings, "tailored")
        else:
            raise
    fields = build_standard_fields(profile, prefs, tailored)
    answers = {"cover_letter": fields.get("cover_letter", "")}
    session = ApplicationSession(
        job_id=job.id,
        run_id=run_id,
        status=status,
        portal_mode=portal.mode,
        cv_source=source,
        cv_file_name=file_name,
        cv_path=path,
        fields=fields,
        answers=answers,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def draft_answers(
    job: Job,
    profile: Profile,
    questions: list[str],
) -> list[dict[str, Any]]:
    cleaned = [question.strip()[:1000] for question in questions if question and question.strip()][:30]
    if not cleaned:
        return []
    profile_payload = profile.as_dict()
    job_payload = {
        "title": job.title,
        "company": job.company,
        "description": job.description[:15000],
        "skills_required": job.skills_required,
        "location": job.location_text,
    }
    result = llm_service.draft_answers(profile_payload, job_payload, cleaned) if llm_service.configured else None
    generated = result.get("answers", []) if isinstance(result, dict) else []
    by_question = {
        str(item.get("question", "")).strip().lower(): item
        for item in generated
        if isinstance(item, dict) and item.get("question")
    }
    answers: list[dict[str, Any]] = []
    for question in cleaned:
        item = by_question.get(question.lower())
        if item is None:
            sensitive = any(marker in question.lower() for marker in SENSITIVE_MARKERS)
            item = {
                "question": question,
                "answer": "",
                "confidence": "low",
                "needs_user_input": True,
                "source": "sensitive" if sensitive else "missing",
            }
        else:
            item["question"] = question
            item.setdefault("needs_user_input", False)
            item.setdefault("confidence", "medium")
            item.setdefault("source", "profile")
        answers.append(item)
    return answers


def job_summary(job: Job, include_description: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": job.id,
        "source": job.source,
        "title": job.title,
        "company": job.company,
        "location_text": job.location_text,
        "city": job.city,
        "country": job.country,
        "remote_type": job.remote_type,
        "remote_scope": job.remote_scope,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "url": job.url,
        "posted_at": job.posted_at,
        "status": job.status,
        "skills_required": list(dict.fromkeys(job.skills_required or [])),
        "skills_nice": list(dict.fromkeys(job.skills_nice or [])),
        "seniority": job.seniority,
        "years_experience": job.years_experience,
        "languages": job.languages or {},
        "red_flags": job.red_flags or [],
        "match": match_to_dict(job.match),
        "portal": _portal_payload(job),
        "imported_manually": bool(job.imported_manually),
        "link_only": bool(job.link_only),
        "requires_login": bool((job.raw_json or {}).get("requires_login")),
        "access_note": str((job.raw_json or {}).get("access_note") or ""),
        "collector": job.collector or job.source,
    }
    if include_description:
        data["description"] = clean_html_text(job.description)
    return data


def session_to_dict(session: ApplicationSession) -> dict[str, Any]:
    portal = None
    if session.job:
        portal = classify_portal(session.job.url).as_dict()
    return {
        "id": session.id,
        "job_id": session.job_id,
        "run_id": session.run_id,
        "status": session.status,
        "portal_mode": session.portal_mode,
        "portal": portal,
        "cv_source": session.cv_source,
        "cv_file_name": session.cv_file_name,
        "cv_url": f"/api/application-sessions/{session.id}/cv",
        "fields": session.fields or {},
        "answers": session.answers or {},
        "message": session.message,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "job": job_summary(session.job, include_description=True) if session.job else None,
    }


def run_item_to_dict(item: ApplicationRunItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "run_id": item.run_id,
        "job_id": item.job_id,
        "session_id": item.session_id,
        "status": item.status,
        "message": item.message,
        "updated_at": item.updated_at,
        "job": job_summary(item.job, include_description=True) if item.job else None,
    }


def run_to_dict(run: ApplicationRun, items: list[ApplicationRunItem]) -> dict[str, Any]:
    return {
        "id": run.id,
        "status": run.status,
        "max_items": run.max_items,
        "total": run.total,
        "submitted": run.submitted,
        "manual": run.manual,
        "failed": run.failed,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
        "items": [run_item_to_dict(item) for item in items],
    }


def _eligible_jobs(db: Session, prefs: Preferences) -> list[Job]:
    stmt = (
        select(Job)
        .options(selectinload(Job.match), selectinload(Job.application))
        .where(Job.status.notin_(("discarded", "dismissed", "applied")))
        .order_by(Job.posted_at.desc())
    )
    jobs = list(db.scalars(stmt).all())
    cutoff = datetime.now(UTC) - timedelta(days=max(1, prefs.freshness_days or 2))
    eligible: list[Job] = []
    for job in jobs:
        if job.link_only:
            continue
        if job.match is None or not job.match.eligible:
            continue
        if job.application is not None and job.application.status in {"applied", "interview", "offer"}:
            continue
        if job.posted_at is None:
            continue
        posted = job.posted_at if job.posted_at.tzinfo else job.posted_at.replace(tzinfo=UTC)
        if posted < cutoff:
            continue
        eligible.append(job)
    return eligible


def start_auto_run(
    db: Session,
    profile: Profile,
    prefs: Preferences,
    settings: Settings,
    max_items: int | None = None,
) -> ApplicationRun:
    limit = max(1, min(int(max_items or prefs.auto_submit_max_per_run or 5), 20))
    eligible = _eligible_jobs(db, prefs)
    auto_jobs: list[Job] = []
    manual_jobs: list[Job] = []
    for job in eligible:
        if classify_portal(job.url, settings).can_auto_submit:
            auto_jobs.append(job)
        else:
            manual_jobs.append(job)
    # Prioritize allowlisted ATS jobs so a page full of manual-only vacancies
    # does not consume the whole run. Remaining slots become manual cards.
    selected_jobs = auto_jobs[:limit]
    selected_jobs.extend(manual_jobs[: max(0, limit - len(selected_jobs))])
    run = ApplicationRun(status="running", max_items=limit, total=len(selected_jobs))
    db.add(run)
    db.commit()
    db.refresh(run)

    for job in selected_jobs:
        portal = classify_portal(job.url, settings)
        if portal.can_auto_submit:
            try:
                session = create_session(
                    db,
                    job,
                    profile,
                    prefs,
                    settings,
                    cv_source=prefs.default_cv_source,
                    run_id=run.id,
                    status="queued",
                )
                item = ApplicationRunItem(
                    run_id=run.id,
                    job_id=job.id,
                    session_id=session.id,
                    status="queued",
                    message=portal.reason,
                )
            except Exception as exc:  # pragma: no cover - filesystem/provider dependent
                logger.exception("Could not prepare auto-submit session for job %s", job.id)
                item = ApplicationRunItem(
                    run_id=run.id,
                    job_id=job.id,
                    status="failed",
                    message=str(exc)[:500],
                )
        else:
            item = ApplicationRunItem(
                run_id=run.id,
                job_id=job.id,
                status="manual",
                message=portal.reason,
            )
        db.add(item)
    db.commit()
    _refresh_run_counts(db, run)
    if run.submitted + run.failed + run.manual >= run.total and run.total > 0:
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        db.commit()
    elif run.total == 0:
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        db.commit()
    db.refresh(run)
    return run


def _refresh_run_counts(db: Session, run: ApplicationRun) -> None:
    items = list(db.scalars(select(ApplicationRunItem).where(ApplicationRunItem.run_id == run.id)).all())
    run.total = len(items)
    run.submitted = len([item for item in items if item.status == "submitted"])
    run.manual = len([item for item in items if item.status == "manual"])
    run.failed = len([item for item in items if item.status == "failed"])
    if run.status == "running" and items and all(
        item.status in {"submitted", "manual", "failed", "skipped"} for item in items
    ):
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
    db.commit()


def claim_next_session(db: Session) -> ApplicationSession | None:
    stale_cutoff = datetime.now(UTC) - timedelta(minutes=5)
    stale = list(
        db.scalars(
            select(ApplicationSession).where(
                ApplicationSession.status == "processing",
                ApplicationSession.updated_at < stale_cutoff,
            )
        ).all()
    )
    for session in stale:
        session.status = "queued"
    if stale:
        db.commit()

    session = db.scalar(
        select(ApplicationSession)
        .options(selectinload(ApplicationSession.job).selectinload(Job.match))
        .where(ApplicationSession.status == "queued")
        .order_by(ApplicationSession.id)
        .limit(1)
    )
    if session is None:
        return None
    session.status = "processing"
    db.commit()
    db.refresh(session)
    return session


def update_session_status(
    db: Session,
    session: ApplicationSession,
    status: str,
    message: str = "",
) -> ApplicationSession:
    normalized = status if status in {"submitted", "manual", "failed", "awaiting_review", "queued"} else "failed"
    session.status = normalized
    session.message = message[:2000]
    item = db.scalar(select(ApplicationRunItem).where(ApplicationRunItem.session_id == session.id))
    if item is not None:
        item.status = normalized
        item.message = message[:2000]
    if normalized == "submitted":
        application = db.scalar(select(Application).where(Application.job_id == session.job_id))
        if application is None:
            application = Application(job_id=session.job_id)
            db.add(application)
        application.status = "applied"
        application.applied_at = datetime.now(UTC)
        application.cv_source = session.cv_source
        application.cv_file_name = session.cv_file_name
        application.portal_mode = session.portal_mode
        application.application_url = session.job.url if session.job else ""
        if session.job is not None:
            session.job.status = "applied"
    if session.run_id:
        run = db.get(ApplicationRun, session.run_id)
        if run is not None:
            _refresh_run_counts(db, run)
    db.commit()
    db.refresh(session)
    return session


def get_run(db: Session, run_id: int) -> tuple[ApplicationRun, list[ApplicationRunItem]] | None:
    run = db.get(ApplicationRun, run_id)
    if run is None:
        return None
    items = list(
        db.scalars(
            select(ApplicationRunItem)
            .options(selectinload(ApplicationRunItem.job).selectinload(Job.match))
            .where(ApplicationRunItem.run_id == run_id)
            .order_by(ApplicationRunItem.id)
        ).all()
    )
    return run, items
