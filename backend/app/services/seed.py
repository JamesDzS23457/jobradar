import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, Job, Match, Preferences, Profile, SearchRun
from app.services.matching import recompute_all
from app.services.search import normalize_job_data, upsert_job

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "demo_jobs.json"


def demo_profile() -> Profile:
    return Profile(
        id=1,
        name="Ana Torres",
        email="ana.torres@example.com",
        phone="+57 300 123 4567",
        location="Bogotá, Colombia",
        headline="Backend Developer · Python · FastAPI · AWS",
        summary=(
            "Desarrolladora backend con 4 años de experiencia construyendo APIs y servicios "
            "en Python. Trabajo con FastAPI, Django, PostgreSQL y AWS. Me gustan los productos "
            "que resuelven problemas reales y los equipos que cuidan la calidad del código."
        ),
        skills=[
            "Python",
            "FastAPI",
            "Django",
            "PostgreSQL",
            "AWS",
            "Docker",
            "Redis",
            "REST APIs",
            "Git",
            "Testing",
            "React",
            "TypeScript",
            "SQL",
        ],
        experience=[
            {
                "company": "FinTech Andina",
                "role": "Backend Developer",
                "dates": "2022 - 2025",
                "bullets": [
                    "Diseñé y construí APIs REST con FastAPI y PostgreSQL para un producto de pagos usado por 40.000 usuarios.",
                    "Reduje en 35% la latencia de los endpoints críticos migrando consultas y añadiendo caché con Redis.",
                    "Implementé pipelines de CI/CD en AWS con Docker y pruebas automatizadas en pytest.",
                    "Trabajé con equipos de producto y frontend para definir contratos de API y mejorar la experiencia.",
                ],
            },
            {
                "company": "Nube Labs",
                "role": "Desarrolladora Backend",
                "dates": "2020 - 2022",
                "bullets": [
                    "Desarrollé módulos de facturación con Django y PostgreSQL para clientes B2B.",
                    "Automaticé procesos operativos con Python y tareas programadas, ahorrando 12 horas semanales.",
                    "Escribí pruebas unitarias y de integración para servicios críticos.",
                ],
            },
        ],
        education=[
            {
                "institution": "Universidad Nacional de Colombia",
                "degree": "Ingeniería de Sistemas",
                "dates": "2016 - 2020",
            }
        ],
        languages={"Español": "Nativo", "Inglés": "B2"},
        links={
            "GitHub": "https://github.com/example",
            "LinkedIn": "https://linkedin.com/in/example",
        },
        years_experience=4,
        raw_cv_text=(
            "Ana Torres\nBackend Developer · Python · FastAPI · AWS\nBogotá, Colombia\n"
            "4 años de experiencia construyendo APIs y servicios en Python."
        ),
    )


def demo_preferences() -> Preferences:
    return Preferences(
        id=1,
        roles=["Backend Developer", "Backend Engineer", "Python Developer", "Full Stack Engineer"],
        keywords=["Python", "FastAPI", "AWS", "PostgreSQL", "Remote"],
        home_city="Bogotá",
        commute_cities=["Chía", "Cota", "Funza", "Mosquera", "Soacha", "La Calera", "Cajicá"],
        country="Colombia",
        remote_preference="any",
        accept_relocation=False,
        accept_international_remote=True,
        timezone="America/Bogota",
        salary_min=9000000,
        currency="COP",
        seniority="mid",
        contract_types=["full-time"],
        languages={"Español": "Nativo", "Inglés": "B2"},
        alert_threshold=85,
        digest_threshold=70,
        digest_hour=8,
        search_interval_hours=6,
    )


def load_demo_jobs() -> list[dict[str, Any]]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def seed_demo(db: Session) -> dict[str, Any]:
    profile = db.get(Profile, 1)
    if profile is None:
        profile = demo_profile()
        db.add(profile)

    prefs = db.get(Preferences, 1)
    if prefs is None:
        prefs = demo_preferences()
        db.add(prefs)

    db.commit()

    new_jobs = 0
    existing_jobs = db.scalar(select(Job.id).limit(1))
    if existing_jobs is None:
        for item in load_demo_jobs():
            normalized = normalize_job_data(item)
            _, is_new = upsert_job(db, normalized)
            new_jobs += 1 if is_new else 0
        db.commit()

    recompute_all(db, profile, prefs)

    if db.scalar(select(SearchRun.id).limit(1)) is None:
        now = datetime.now(UTC)
        total = len(load_demo_jobs())
        db.add(
            SearchRun(
                started_at=now,
                finished_at=now,
                found=total,
                new=total,
                sources={"demo": total},
                errors=[],
            )
        )
        db.commit()

    applications = db.scalar(select(Application.id).limit(1))
    if applications is None:
        top_matches = list(db.scalars(select(Match).where(Match.eligible.is_(True)).order_by(Match.score.desc()).limit(2)).all())
        statuses = ["applied", "interview"]
        for index, match in enumerate(top_matches):
            db.add(
                Application(
                    job_id=match.job_id,
                    status=statuses[index] if index < len(statuses) else "applied",
                    notes="Postulación de ejemplo del modo demo.",
                )
            )
        db.commit()

    return {
        "jobs": len(load_demo_jobs()),
        "new_jobs": new_jobs,
        "matches": db.scalar(select(Match.id).limit(1)) is not None,
        "applications": db.scalar(select(Application.id).limit(1)) is not None,
    }


def reset_demo(db: Session) -> dict[str, Any]:
    from app.models import AlertLog, Feedback, SearchRun, TailoredCV

    db.query(AlertLog).delete()
    db.query(Feedback).delete()
    db.query(TailoredCV).delete()
    db.query(Application).delete()
    db.query(Match).delete()
    db.query(Job).delete()
    db.query(SearchRun).delete()
    db.query(Preferences).delete()
    db.query(Profile).delete()
    db.commit()
    return seed_demo(db)
