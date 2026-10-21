import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import Settings, get_settings
from app.core.db import SessionLocal
from app.models import Preferences, Profile
from app.services.emailer import send_digest
from app.services.search import run_search

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _scheduled_search() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        profile = db.get(Profile, 1)
        prefs = db.get(Preferences, 1)
        if profile is None or prefs is None:
            logger.info("Scheduler skipped: profile or preferences missing")
            return
        run = run_search(db, profile, prefs, settings)
        logger.info("Scheduled search finished: found=%s new=%s", run.found, run.new)
    except Exception:
        logger.exception("Scheduled search failed")
    finally:
        db.close()


def _scheduled_digest() -> None:
    settings = get_settings()
    if settings.demo_mode:
        return
    db = SessionLocal()
    try:
        prefs = db.get(Preferences, 1)
        if prefs is None:
            return
        try:
            now = datetime.now(ZoneInfo(prefs.timezone or settings.timezone))
        except Exception:
            now = datetime.now(ZoneInfo(settings.timezone))
        if now.hour != prefs.digest_hour:
            return
        sent = send_digest(db, settings)
        if sent:
            logger.info("Scheduled digest sent: %s jobs", sent)
    except Exception:
        logger.exception("Scheduled digest failed")
    finally:
        db.close()


def start_scheduler(settings: Settings | None = None) -> BackgroundScheduler | None:
    global _scheduler
    settings = settings or get_settings()
    if not settings.enable_scheduler:
        return None
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone=settings.timezone)
    _scheduler.add_job(
        _scheduled_search,
        "interval",
        hours=max(1, settings.search_interval_hours),
        id="jobradar-search",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _scheduled_digest,
        "cron",
        minute=0,
        id="jobradar-digest",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler started: search every %s hours, digest checked hourly", settings.search_interval_hours)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
