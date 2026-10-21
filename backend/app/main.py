import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import SessionLocal, init_db
from app.services.scheduler import shutdown_scheduler, start_scheduler
from app.services.seed import seed_demo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.demo_mode:
        db = SessionLocal()
        try:
            seed_demo(db)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
