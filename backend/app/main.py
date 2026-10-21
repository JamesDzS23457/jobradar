import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import SessionLocal, init_db
from app.models import Preferences, Profile
from app.services.matching import recompute_all
from app.services.scheduler import shutdown_scheduler, start_scheduler
from app.services.search import clear_legacy_search_errors
from app.services.seed import seed_demo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        cleared = clear_legacy_search_errors(db)
        if cleared:
            logger.info("Cleared obsolete search errors from %s run(s)", cleared)
        if settings.demo_mode:
            seed_demo(db)
        else:
            profile = db.get(Profile, 1)
            prefs = db.get(Preferences, 1)
            if profile is not None and prefs is not None:
                # Apply current matching rules (language, seniority filters)
                # to jobs that were imported with an older version.
                try:
                    recompute_all(db, profile, prefs)
                except Exception:
                    logger.exception("Startup match recomputation failed")
                    db.rollback()
    finally:
        db.close()
    start_scheduler(settings)
    yield
    shutdown_scheduler()


app = FastAPI(
    title="JobRadar API",
    description="Copiloto personal de búsqueda y postulación laboral.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"(chrome-extension://.*|http://(localhost|127\.0\.0\.1):\d+)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "demo_mode": settings.demo_mode,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "demo_mode": settings.demo_mode}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
