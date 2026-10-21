from app.core.db import SessionLocal
from app.models import Job
from app.services.search import canonical_url, normalize_job_data, upsert_job


def test_canonical_url_removes_tracking_and_fragment():
    assert canonical_url(
        "https://www.linkedin.com/jobs/view/123?trackingId=abc&trk=public&utm_source=x#frag"
    ) == "https://linkedin.com/jobs/view/123"


def test_upsert_reuses_job_with_same_canonical_url():
    first = normalize_job_data(
        {
            "source": "jsearch",
            "external_id": "run-1",
            "title": "Backend Developer",
            "company": "Acme",
            "description": "Python",
            "location_text": "Bogotá",
            "url": "https://www.linkedin.com/jobs/view/123?trackingId=first#x",
        }
    )
    second = normalize_job_data(
        {
            "source": "jsearch",
            "external_id": "run-2",
            "title": "Backend Developer",
            "company": "Acme",
            "description": "Python and FastAPI",
            "location_text": "Bogotá, Colombia",
            "url": "https://www.linkedin.com/jobs/view/123?trackingId=second#y",
        }
    )
    assert first["hash"] != second["hash"]
    assert first["dedupe_key"] == second["dedupe_key"]

    with SessionLocal() as db:
        job, created = upsert_job(db, first)
        db.commit()
        job_id = job.id
        existing, created_again = upsert_job(db, second, refresh=True)
        db.commit()
        assert created is True
        assert created_again is False
        assert existing.id == job_id
        assert existing.description == "Python and FastAPI"
        saved = db.get(Job, job_id)
        assert saved is not None
        db.delete(saved)
        db.commit()


def test_detects_listing_pages_not_individual_jobs():
    from app.models import Job
    from app.services.search import is_listing_page

    assert is_listing_page(Job(title="Empleos", url="https://es.linkedin.com/jobs/desarrollo-web-empleos"))
    assert is_listing_page(Job(title="Trabajo de backend", url="https://co.indeed.com/q-backend-empleos.html"))
    assert is_listing_page(Job(title="Trabajo de backend", url="https://co.computrabajo.com/trabajo-de-backend"))
    assert is_listing_page(
        Job(
            title="Postúlate a las ofertas de empleo de Backend en Colombia",
            url="https://www.elempleo.com/co/ofertas-empleo/trabajo-backend",
        )
    )
    assert not is_listing_page(Job(title="Backend Developer", url="https://www.linkedin.com/jobs/view/123"))
    assert not is_listing_page(
        Job(
            title="Backend Developer",
            url="https://co.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-backend-123",
        )
    )
