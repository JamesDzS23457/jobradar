import logging
import mimetypes
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.db import get_db
from app.models import (
    Application,
    ApplicationRun,
    ApplicationRunItem,
    ApplicationSession,
    Job,
    Match,
    Preferences,
    Profile,
    SearchRun,
    TailoredCV,
)
from app.schemas import (
    ApplicationCreate,
    ApplicationSessionCreate,
    ApplicationUpdate,
    AutoRunRequest,
    DraftAnswersRequest,
    JobStatusUpdate,
    JobUrlImport,
    PreferencesUpdate,
    ProfileUpdate,
    SessionStatusUpdate,
    TailoredUpdate,
)
from app.services.applications import (
    build_preview,
    create_session,
    draft_answers,
    get_run,
    original_cv_path,
    run_to_dict,
    session_to_dict,
    start_auto_run,
    update_session_status,
)
from app.services.career import suggest_search_preferences
from app.services.cv_parser import (
    extract_text,
    find_skills,
    normalize_parsed_profile,
    parse_profile_heuristic,
)
from app.services.emailer import send_test_email
from app.services.job_import import (
    JobImportError,
    JobLinkOnlyError,
    import_job_from_url,
    link_only_payload,
)
from app.services.llm import llm_service
from app.services.matching import (
    canonical_skill,
    compute_match,
    match_to_dict,
    recompute_all,
    upsert_match,
)
from app.services.portals import classify_portal
from app.services.search import latest_search_run, normalize_job_data, run_search, upsert_job
from app.services.seed import reset_demo, seed_demo
from app.services.tailoring import export_docx, export_pdf, generate_tailored, tailored_to_dict
from app.services.text_clean import clean_html_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
settings = get_settings()


def _profile(db: Session) -> Profile | None:
    return db.get(Profile, 1)


def _prefs(db: Session) -> Preferences:
    prefs = db.get(Preferences, 1)
    if prefs is None:
        prefs = Preferences(
            id=1,
            freshness_days=settings.freshness_days,
            auto_submit_enabled=settings.auto_submit_enabled,
            auto_submit_max_per_run=settings.auto_submit_max_per_run,
            default_cv_source=settings.default_cv_source,
            alert_threshold=settings.alert_threshold,
            digest_threshold=settings.digest_threshold,
            digest_hour=settings.digest_hour,
            search_interval_hours=settings.search_interval_hours,
            timezone=settings.timezone,
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def _profile_dict(profile: Profile | None) -> dict | None:
    if profile is None:
        return None
    data = profile.as_dict()
    data["has_cv"] = bool(profile.cv_file_path)
    data["cv_file_name"] = Path(profile.cv_file_path).name if profile.cv_file_path else ""
    data["cv_original_url"] = "/api/cv/original" if original_cv_path(profile) else ""
    return data


def _portal_dict(job: Job) -> dict[str, object]:
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


def _job_dict(job: Job, include_description: bool = False) -> dict:
    data = {
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
        "portal": _portal_dict(job),
        "imported_manually": bool(job.imported_manually),
        "link_only": bool(job.link_only),
        "requires_login": bool((job.raw_json or {}).get("requires_login")),
        "access_note": str((job.raw_json or {}).get("access_note") or ""),
        "collector": job.collector or job.source,
    }
    if include_description:
        data["description"] = clean_html_text(job.description)
    return data


def _application_dict(application: Application) -> dict:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "status": application.status,
        "applied_at": application.applied_at,
        "notes": application.notes,
        "next_action_at": application.next_action_at,
        "cv_source": application.cv_source,
        "cv_file_name": application.cv_file_name,
        "portal_mode": application.portal_mode,
        "application_url": application.application_url,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "job": _job_dict(application.job) if application.job else None,
    }


def _run_dict(run: SearchRun | None) -> dict | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "found": run.found,
        "new": run.new,
        "sources": run.sources,
        "errors": run.errors,
    }


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "demo_mode": settings.demo_mode}


@router.get("/config/status")
def config_status() -> dict:
    return {
        "app_name": settings.app_name,
        "demo_mode": settings.demo_mode,
        "llm_configured": settings.llm_configured,
        "llm_provider": settings.llm_provider,
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model_quality if settings.llm_configured else None,
        "llm_model_fast": settings.llm_model_fast,
        "llm_model_quality": settings.llm_model_quality,
        "llm_model_fallback": settings.llm_model_fallback,
        "auto_submit_enabled": settings.auto_submit_enabled,
        "auto_submit_max_per_run": settings.auto_submit_max_per_run,
        "auto_submit_portals": settings.auto_submit_portals_list,
        "manual_only_portals": settings.manual_only_portals_list,
        "default_cv_source": settings.default_cv_source,
        "smtp_configured": settings.smtp_configured,
        "jsearch_configured": settings.jsearch_configured,
        "jooble_configured": settings.jooble_configured,
        "web_search_provider": settings.web_search_provider,
        "tavily_configured": settings.tavily_configured,
        "tavily_keyless": settings.tavily_keyless,
        "brave_configured": settings.brave_configured,
        "scheduler_enabled": settings.enable_scheduler,
        "alert_threshold": settings.alert_threshold,
        "database": "sqlite" if settings.database_url.startswith("sqlite") else "external",
    }


@router.post("/llm/test")
def test_llm() -> dict:
    return llm_service.test_connection()


@router.get("/portals/classify")
def classify_portal_url(url: str = Query(min_length=3, max_length=2000)) -> dict:
    return {"portal": classify_portal(url, settings).as_dict()}


@router.get("/cv/original")
def download_original_cv(db: Session = Depends(get_db)) -> FileResponse:
    profile = _profile(db)
    path = original_cv_path(profile)
    if path is None:
        raise HTTPException(status_code=404, detail="No hay un CV original disponible.")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/profile")
def get_profile(db: Session = Depends(get_db)) -> dict:
    profile = _profile(db)
    return {"exists": profile is not None, "profile": _profile_dict(profile)}


@router.put("/profile")
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db)) -> dict:
    profile = _profile(db)
    if profile is None:
        profile = Profile(id=1)
        db.add(profile)
    updates = payload.model_dump(exclude_unset=True)
    if "skills" in updates and updates["skills"] is not None:
        updates["skills"] = list(dict.fromkeys(canonical_skill(skill) for skill in updates["skills"] if skill.strip()))
    for key, value in updates.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    warning = ""
    try:
        recompute_all(db, profile, _prefs(db))
    except Exception as exc:
        logger.exception("Profile saved but match recomputation failed")
        db.rollback()
        warning = f"Perfil guardado, pero no se pudieron recalcular los matches: {exc}"
    return {"profile": _profile_dict(profile), "warning": warning}


@router.get("/preferences")
def get_preferences(db: Session = Depends(get_db)) -> dict:
    return {"preferences": _prefs(db).as_dict()}


@router.put("/preferences")
def update_preferences(payload: PreferencesUpdate, db: Session = Depends(get_db)) -> dict:
    prefs = _prefs(db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, key, value)
    db.commit()
    db.refresh(prefs)
    profile = _profile(db)
    warning = ""
    if profile is not None:
        try:
            recompute_all(db, profile, prefs)
        except Exception as exc:
            logger.exception("Preferences saved but match recomputation failed")
            db.rollback()
            warning = f"Preferencias guardadas, pero no se pudieron recalcular los matches: {exc}"
    return {"preferences": prefs.as_dict(), "warning": warning}


@router.post("/cv/upload")
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    filename = file.filename or "cv.pdf"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa PDF, DOCX, TXT o MD.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo supera los 10 MB.")
    try:
        text = extract_text(filename, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el CV: {exc}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="No se encontró texto en el archivo. Si es un PDF escaneado, usa DOCX o TXT.")

    settings.ensure_dirs()
    stored_name = f"{uuid4().hex}_{Path(filename).name}"
    stored_path = settings.upload_dir / stored_name
    stored_path.write_bytes(content)

    parsed = llm_service.extract_profile(text) if llm_service.configured else None
    parsed_with = "llm" if parsed else "heuristic"
    if not parsed:
        parsed = parse_profile_heuristic(text)
    parsed = normalize_parsed_profile(parsed) if isinstance(parsed, dict) else {}

    profile = _profile(db)
    if profile is None:
        profile = Profile(id=1)
        db.add(profile)

    fields = [
        "name",
        "email",
        "phone",
        "location",
        "headline",
        "summary",
        "skills",
        "experience",
        "education",
        "languages",
        "links",
        "years_experience",
    ]
    for field in fields:
        value = parsed.get(field)
        if value not in (None, "", [], {}):
            if field == "skills":
                value = list(dict.fromkeys(canonical_skill(str(skill)) for skill in value))
            setattr(profile, field, value)
    if not parsed.get("skills"):
        profile.skills = find_skills(text)
    if not parsed.get("years_experience"):
        from app.services.cv_parser import extract_years_experience

        profile.years_experience = extract_years_experience(text)

    profile.raw_cv_text = text
    profile.cv_file_path = str(stored_path)
    db.commit()
    db.refresh(profile)

    prefs = _prefs(db)
    suggestions = suggest_search_preferences(profile, text)
    if suggestions.get("roles"):
        prefs.roles = list(suggestions["roles"])
    if suggestions.get("keywords"):
        prefs.keywords = list(suggestions["keywords"])
    db.commit()
    db.refresh(prefs)
    recompute_all(db, profile, prefs)
    return {
        "profile": _profile_dict(profile),
        "parsed_with": parsed_with,
        "skills_found": profile.skills,
        "search_suggestions": suggestions,
        "review": {
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "headline": profile.headline,
            "skills": profile.skills,
            "experience_count": len(profile.experience or []),
            "education_count": len(profile.education or []),
            "languages": profile.languages or {},
            "links": profile.links or {},
            "warnings": parsed.get("warnings", []) if isinstance(parsed, dict) else [],
        },
        "message": (
            "CV procesado correctamente. Revisa los datos detectados y los roles de búsqueda antes de postular."
            if parsed_with == "llm"
            else "CV procesado con el lector local. Revisa los datos detectados y los roles de búsqueda."
        ),
    }


@router.post("/search/run")
def search_now(db: Session = Depends(get_db)) -> dict:
    profile = _profile(db)
    if profile is None:
        raise HTTPException(status_code=400, detail="Primero sube tu CV o carga el modo demo.")
    prefs = _prefs(db)
    run = run_search(db, profile, prefs, settings)
    return {"run": _run_dict(run)}


@router.get("/search/status")
def search_status(db: Session = Depends(get_db)) -> dict:
    return {"run": _run_dict(latest_search_run(db))}


@router.post("/jobs/import-url")
def import_job(payload: JobUrlImport, db: Session = Depends(get_db)) -> dict:
    """Import a public job URL, score it against the CV and keep the portal link."""
    profile = _profile(db)
    if profile is None:
        raise HTTPException(status_code=400, detail="Primero sube tu CV o carga el modo demo.")
    try:
        extracted, extracted_with = import_job_from_url(payload.url)
    except JobImportError as exc:
        portal = classify_portal(payload.url, settings)
        is_http = payload.url.strip().lower().startswith(("http://", "https://"))
        if is_http and (isinstance(exc, JobLinkOnlyError) or portal.mode == "manual_only"):
            try:
                extracted = link_only_payload(payload.url, str(exc), portal.label)
            except JobImportError as fallback_exc:
                raise HTTPException(status_code=400, detail=str(fallback_exc)) from fallback_exc
            normalized = normalize_job_data(extracted)
            job, created = upsert_job(db, normalized, refresh=True)
            job.imported_manually = True
            job.link_only = True
            job.collector = "manual"
            result = compute_match(profile, _prefs(db), job)
            upsert_match(db, job, result)
            db.commit()
            db.refresh(job)
            return {
                "job": _job_dict(job, include_description=True),
                "created": created,
                "extracted_with": "link_only",
                "link_only": True,
                "message": (
                    "Guardamos el enlace. Este portal requiere iniciar sesión o no permite "
                    "leer la vacante automáticamente; ábrelo para ver los detalles y postularte."
                ),
            }
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized = normalize_job_data(extracted)
    if not normalized["title"]:
        raise HTTPException(status_code=400, detail="No se encontró el título de la vacante.")
    job, created = upsert_job(db, normalized, refresh=True)
    job.imported_manually = True
    job.collector = "manual"
    result = compute_match(profile, _prefs(db), job)
    upsert_match(db, job, result)
    db.commit()
    db.refresh(job)
    return {
        "job": _job_dict(job, include_description=True),
        "created": created,
        "extracted_with": extracted_with,
    }


@router.get("/jobs")
def list_jobs(
    q: str | None = Query(default=None),
    remote_type: str | None = Query(default=None),
    min_score: float | None = Query(default=None, ge=0, le=100),
    saved: bool = Query(default=False),
    discarded: bool = Query(default=False),
    include_ineligible: bool = Query(default=False),
    max_age_days: int | None = Query(default=None, ge=1, le=365),
    include_unknown_date: bool = Query(default=False),
    limit: int = Query(default=60, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Job).options(selectinload(Job.match)).order_by(Job.posted_at.desc())
    stmt = stmt.where(Job.status == "discarded") if discarded else stmt.where(Job.status != "discarded")
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(Job.title.ilike(pattern) | Job.company.ilike(pattern) | Job.description.ilike(pattern))
    if remote_type:
        stmt = stmt.where(Job.remote_type == remote_type)
    if saved:
        stmt = stmt.where(Job.status == "saved")
    if max_age_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        freshness = (Job.posted_at >= cutoff) | Job.imported_manually.is_(True) | Job.link_only.is_(True)
        if include_unknown_date:
            freshness = freshness | Job.posted_at.is_(None)
        stmt = stmt.where(freshness)
    jobs = list(db.scalars(stmt).all())
    items = []
    for job in jobs:
        match = job.match
        if not include_ineligible and (match is None or not match.eligible):
            continue
        if min_score is not None and (match is None or match.score < min_score):
            continue
        items.append(_job_dict(job))

    def sort_key(item: dict) -> tuple[float, float]:
        posted_at = item.get("posted_at")
        timestamp = posted_at.timestamp() if posted_at is not None else 0.0
        return (timestamp, item["match"]["score"] if item["match"] else 0.0)

    items.sort(key=sort_key, reverse=True)
    total = len(items)
    return {"items": items[offset : offset + limit], "total": total}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.scalar(select(Job).options(selectinload(Job.match)).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return {"job": _job_dict(job, include_description=True)}


@router.patch("/jobs/{job_id}")
def update_job(job_id: int, payload: JobStatusUpdate, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    application = db.scalar(select(Application).where(Application.job_id == job_id))
    if payload.status == "saved":
        if application is None:
            application = Application(job_id=job_id, status="saved")
            db.add(application)
            job.status = "saved"
        elif application.status == "saved":
            job.status = "saved"
        elif application.status in {"applied", "interview", "offer"}:
            job.status = "applied"
        else:
            job.status = "dismissed" if application.status == "rejected" else "saved"
    elif payload.status == "new":
        if application is not None and application.status == "saved":
            db.delete(application)
        job.status = "new"
    else:
        job.status = payload.status
    db.commit()
    db.refresh(job)
    return {"job": _job_dict(job)}


@router.delete("/jobs/{job_id}")
def discard_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    job.status = "discarded"
    db.commit()
    db.refresh(job)
    return {"discarded": True, "job": _job_dict(job)}


@router.post("/jobs/{job_id}/restore")
def restore_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    application = db.scalar(select(Application).where(Application.job_id == job_id))
    if application is not None and application.status in {"applied", "interview", "offer"}:
        job.status = "applied"
    elif application is not None and application.status == "saved":
        job.status = "saved"
    else:
        job.status = "new"
    db.commit()
    db.refresh(job)
    return {"restored": True, "job": _job_dict(job)}


@router.post("/jobs/{job_id}/match")
def recompute_one(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    profile = _profile(db)
    if job is None or profile is None:
        raise HTTPException(status_code=404, detail="Vacante o perfil no encontrado")
    result = compute_match(profile, _prefs(db), job)
    match = upsert_match(db, job, result)
    db.commit()
    db.refresh(match)
    return {"match": match_to_dict(match)}


@router.post("/jobs/{job_id}/tailor")
def tailor_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    profile = _profile(db)
    if job is None or profile is None:
        raise HTTPException(status_code=404, detail="Vacante o perfil no encontrado")
    tailored = generate_tailored(db, job, profile, job.match, settings)
    return {"tailored": tailored_to_dict(tailored)}


@router.get("/tailored/{tailored_id}")
def get_tailored(tailored_id: int, db: Session = Depends(get_db)) -> dict:
    tailored = db.get(TailoredCV, tailored_id)
    if tailored is None:
        raise HTTPException(status_code=404, detail="CV adaptado no encontrado")
    return {"tailored": tailored_to_dict(tailored)}


@router.put("/tailored/{tailored_id}")
def update_tailored(tailored_id: int, payload: TailoredUpdate, db: Session = Depends(get_db)) -> dict:
    tailored = db.get(TailoredCV, tailored_id)
    if tailored is None:
        raise HTTPException(status_code=404, detail="CV adaptado no encontrado")
    if payload.content is not None:
        tailored.content = payload.content
    if payload.approved is not None:
        tailored.approved = payload.approved
    db.commit()
    db.refresh(tailored)
    return {"tailored": tailored_to_dict(tailored)}


@router.get("/tailored/{tailored_id}/download")
def download_tailored(tailored_id: int, format: str = Query(default="docx", pattern="^(docx|pdf)$"), db: Session = Depends(get_db)) -> FileResponse:
    tailored = db.get(TailoredCV, tailored_id)
    profile = _profile(db)
    if tailored is None or profile is None:
        raise HTTPException(status_code=404, detail="CV adaptado no encontrado")
    if not tailored.approved:
        raise HTTPException(status_code=403, detail="Aprueba el CV antes de descargarlo.")
    path = Path(tailored.docx_path if format == "docx" else tailored.pdf_path)
    if not path.exists():
        path = export_docx(tailored, profile, settings) if format == "docx" else export_pdf(tailored, profile, settings)
        if format == "docx":
            tailored.docx_path = str(path)
        else:
            tailored.pdf_path = str(path)
        db.commit()
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "docx"
        else "application/pdf"
    )
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/jobs/{job_id}/application")
def application_preview(
    job_id: int,
    cv_source: str | None = Query(default=None, pattern="^(tailored|original)$"),
    db: Session = Depends(get_db),
) -> dict:
    job = db.scalar(select(Job).options(selectinload(Job.match)).where(Job.id == job_id))
    profile = _profile(db)
    if job is None or profile is None:
        raise HTTPException(status_code=404, detail="Vacante o perfil no encontrado")
    return {"preview": build_preview(db, job, profile, _prefs(db), settings, cv_source)}


@router.post("/jobs/{job_id}/application-session")
def prepare_application_session(
    job_id: int,
    payload: ApplicationSessionCreate | None = None,
    db: Session = Depends(get_db),
) -> dict:
    job = db.scalar(select(Job).options(selectinload(Job.match)).where(Job.id == job_id))
    profile = _profile(db)
    if job is None or profile is None:
        raise HTTPException(status_code=404, detail="Vacante o perfil no encontrado")
    try:
        session = create_session(
            db,
            job,
            profile,
            _prefs(db),
            settings,
            cv_source=payload.cv_source if payload else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session = db.scalar(
        select(ApplicationSession)
        .options(selectinload(ApplicationSession.job).selectinload(Job.match))
        .where(ApplicationSession.id == session.id)
    )
    return {"session": session_to_dict(session) if session else None}


@router.get("/application-sessions/{session_id}")
def get_application_session(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = db.scalar(
        select(ApplicationSession)
        .options(selectinload(ApplicationSession.job).selectinload(Job.match))
        .where(ApplicationSession.id == session_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión de postulación no encontrada")
    return {"session": session_to_dict(session)}


@router.get("/application-sessions/{session_id}/cv")
def download_session_cv(session_id: int, db: Session = Depends(get_db)) -> FileResponse:
    session = db.get(ApplicationSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión de postulación no encontrada")
    path = Path(session.cv_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="El CV de esta postulación ya no está disponible.")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=session.cv_file_name or path.name)


@router.post("/applications/draft-answers")
def draft_application_answers(payload: DraftAnswersRequest, db: Session = Depends(get_db)) -> dict:
    job = db.scalar(select(Job).options(selectinload(Job.match)).where(Job.id == payload.job_id))
    profile = _profile(db)
    if job is None or profile is None:
        raise HTTPException(status_code=404, detail="Vacante o perfil no encontrado")
    return {"answers": draft_answers(job, profile, payload.questions)}


@router.post("/applications/auto-run")
def auto_run(payload: AutoRunRequest | None = None, db: Session = Depends(get_db)) -> dict:
    profile = _profile(db)
    prefs = _prefs(db)
    if profile is None:
        raise HTTPException(status_code=400, detail="Primero sube tu CV o carga el modo demo.")
    if not prefs.auto_submit_enabled:
        raise HTTPException(
            status_code=400,
            detail="Activa el auto-envío en Ajustes antes de iniciar una ronda.",
        )
    run = start_auto_run(
        db,
        profile,
        prefs,
        settings,
        max_items=payload.max_items if payload else None,
    )
    loaded = get_run(db, run.id)
    if loaded is None:
        raise HTTPException(status_code=500, detail="No se pudo cargar la ronda.")
    run, items = loaded
    return {"run": run_to_dict(run, items)}


@router.get("/application-runs/{run_id}")
def application_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    loaded = get_run(db, run_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Ronda de postulaciones no encontrada")
    run, items = loaded
    return {"run": run_to_dict(run, items)}


@router.get("/extension/next")
def extension_next(db: Session = Depends(get_db)) -> dict:
    from app.services.applications import claim_next_session

    session = claim_next_session(db)
    if session is None:
        return {"session": None}
    session = db.scalar(
        select(ApplicationSession)
        .options(selectinload(ApplicationSession.job).selectinload(Job.match))
        .where(ApplicationSession.id == session.id)
    )
    return {"session": session_to_dict(session) if session else None}


@router.post("/extension/sessions/{session_id}/status")
def extension_session_status(
    session_id: int,
    payload: SessionStatusUpdate,
    db: Session = Depends(get_db),
) -> dict:
    session = db.scalar(
        select(ApplicationSession)
        .options(selectinload(ApplicationSession.job).selectinload(Job.match))
        .where(ApplicationSession.id == session_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión de postulación no encontrada")
    session = update_session_status(db, session, payload.status, payload.message)
    return {"session": session_to_dict(session)}


@router.get("/applications")
def list_applications(db: Session = Depends(get_db)) -> dict:
    applications = list(
        db.scalars(
            select(Application)
            .options(selectinload(Application.job).selectinload(Job.match))
            .order_by(Application.updated_at.desc())
        ).all()
    )
    return {"items": [_application_dict(application) for application in applications]}


@router.post("/applications")
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    application = db.scalar(select(Application).where(Application.job_id == payload.job_id))
    if application is None:
        application = Application(job_id=payload.job_id)
        db.add(application)
    application.status = payload.status
    application.notes = payload.notes
    application.next_action_at = payload.next_action_at
    if payload.cv_source:
        application.cv_source = payload.cv_source
        application.portal_mode = classify_portal(job.url, settings).mode
        application.application_url = job.url
    if payload.status in {"applied", "interview", "offer"} and application.applied_at is None:
        application.applied_at = datetime.now(UTC)
    job.status = "applied" if payload.status in {"applied", "interview", "offer"} else "saved"
    db.commit()
    db.refresh(application)
    return {"application": _application_dict(application)}


@router.patch("/applications/{application_id}")
def update_application(application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)) -> dict:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(application, key, value)
    if payload.status in {"applied", "interview", "offer"} and application.applied_at is None:
        application.applied_at = datetime.now(UTC)
    if payload.status:
        application.job.status = (
            "applied" if payload.status in {"applied", "interview", "offer"} else "dismissed" if payload.status == "rejected" else "saved"
        )
    db.commit()
    db.refresh(application)
    return {"application": _application_dict(application)}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    profile = _profile(db)
    prefs = _prefs(db)
    jobs = [
        job
        for job in db.scalars(select(Job).options(selectinload(Job.match))).all()
        if job.status != "discarded"
    ]
    eligible_jobs = [job for job in jobs if job.match and job.match.eligible]
    applications = list(
        db.scalars(
            select(Application)
            .options(selectinload(Application.job).selectinload(Job.match))
            .order_by(Application.updated_at.desc())
        ).all()
    )
    scores = [job.match.score for job in eligible_jobs if job.match]
    stats = {
        "total_jobs": len(jobs),
        "eligible_jobs": len(eligible_jobs),
        "excellent": len([score for score in scores if score >= 85]),
        "good": len([score for score in scores if 70 <= score < 85]),
        "applied": len([app for app in applications if app.status == "applied"]),
        "interviews": len([app for app in applications if app.status == "interview"]),
        "offers": len([app for app in applications if app.status == "offer"]),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
    }
    top = sorted(eligible_jobs, key=lambda job: job.match.score if job.match else 0, reverse=True)[:5]
    distribution = [
        {"range": "85–100", "count": len([score for score in scores if score >= 85])},
        {"range": "70–84", "count": len([score for score in scores if 70 <= score < 85])},
        {"range": "55–69", "count": len([score for score in scores if 55 <= score < 70])},
        {"range": "0–54", "count": len([score for score in scores if score < 55])},
    ]
    return {
        "profile_complete": bool(profile and profile.name and profile.skills),
        "profile_name": profile.name if profile else "",
        "headline": profile.headline if profile else "",
        "home_city": prefs.home_city,
        "stats": stats,
        "top_matches": [_job_dict(job) for job in top],
        "distribution": distribution,
        "last_run": _run_dict(latest_search_run(db)),
        "recent_applications": [_application_dict(application) for application in applications[:5]],
    }


@router.post("/alerts/test-email")
def test_email() -> dict:
    ok, message = send_test_email(settings)
    return {"sent": ok, "message": message or "Correo enviado correctamente."}


@router.post("/demo/seed")
def demo_seed(db: Session = Depends(get_db)) -> dict:
    return {"seeded": seed_demo(db)}


@router.post("/demo/reset")
def demo_reset(db: Session = Depends(get_db)) -> dict:
    shutil.rmtree(settings.upload_dir, ignore_errors=True)
    shutil.rmtree(settings.export_dir, ignore_errors=True)
    settings.ensure_dirs()
    return {"reset": reset_demo(db)}


@router.delete("/data")
def delete_data(db: Session = Depends(get_db)) -> dict:
    from app.models import AlertLog, Feedback

    db.query(AlertLog).delete()
    db.query(Feedback).delete()
    db.query(ApplicationRunItem).delete()
    db.query(ApplicationSession).delete()
    db.query(ApplicationRun).delete()
    db.query(TailoredCV).delete()
    db.query(Application).delete()
    db.query(Match).delete()
    db.query(Job).delete()
    db.query(SearchRun).delete()
    db.query(Preferences).delete()
    db.query(Profile).delete()
    db.commit()
    shutil.rmtree(settings.upload_dir, ignore_errors=True)
    shutil.rmtree(settings.export_dir, ignore_errors=True)
    settings.ensure_dirs()
    return {"deleted": True}
