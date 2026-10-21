import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.job_import import extract_job_from_html
from app.services.seed import demo_preferences
from app.services.sources.websearch import WebSearchSource


def test_extracts_jsonld_jobposting():
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "name": "Acme",
            },
            {
                "@type": "JobPosting",
                "title": "[Hiring] Backend Engineer @Acme",
                "description": "<p>We need Python, Docker and PostgreSQL.</p>",
                "datePosted": "2026-10-20T10:00:00+00:00",
                "jobLocationType": "TELECOMMUTE",
                "applicantLocationRequirements": [
                    {"@type": "Country", "name": "CO"},
                    {"@type": "Country", "name": "MX"},
                ],
                "hiringOrganization": {"@type": "Organization", "name": "Acme"},
                "baseSalary": {
                    "currency": "COP",
                    "value": {
                        "minValue": 8000000,
                        "maxValue": 12000000,
                        "unitText": "MONTH",
                    },
                },
            },
        ],
    }
    html = f'<script type="application/ld+json">{json.dumps(payload)}</script>'

    job, method = extract_job_from_html(html, "https://www.computrabajo.com.co/oferta/123")

    assert method == "jsonld"
    assert job["title"] == "Backend Engineer"
    assert job["company"] == "Acme"
    assert job["source"] == "computrabajo"
    assert job["remote_type"] == "remote"
    assert job["remote_scope"] == "colombia"
    assert job["location_text"] == "Remoto (Colombia)"
    assert job["salary_min"] == 8000000
    assert job["salary_max"] == 12000000
    assert job["currency"] == "COP"
    assert "Python" in job["skills_required"]


def test_metadata_fallback_cleans_site_suffix():
    html = """
    <html>
      <head>
        <meta property="og:title" content="Data Engineer | Acme Labs" />
        <meta property="og:site_name" content="Acme Labs" />
        <meta name="description" content="Build reliable data pipelines with Python and SQL." />
      </head>
      <body><h1>Data Engineer</h1></body>
    </html>
    """

    job, method = extract_job_from_html(html, "https://acme.example/jobs/data-engineer")

    assert method == "metadata"
    assert job["title"] == "Data Engineer"
    assert job["company"] == "Acme Labs"
    assert job["url"] == "https://acme.example/jobs/data-engineer"
    assert "Python" in job["skills_required"]


def test_websearch_builds_targeted_queries_and_filters_urls():
    source = WebSearchSource("test-key")
    queries = source._queries(demo_preferences())

    assert any("computrabajo.com.co" in query for query in queries)
    assert any("elempleo.com" in query for query in queries)
    assert source._looks_like_job("https://co.computrabajo.com/oferta/123")
    assert source._looks_like_job("https://boards.greenhouse.io/acme/jobs/123")
    assert source._looks_like_job("https://www.linkedin.com/jobs/view/123")
    assert source._looks_like_job("https://co.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-backend-123")
    assert source._looks_like_job("https://www.elempleo.com/co/ofertas-empleo/bogota/trabajo-desarrollador-backend")
    assert not source._looks_like_job("https://www.indeed.com/jobs?q=backend")
    assert not source._looks_like_job("https://es.linkedin.com/jobs/desarrollo-web-empleos")
    assert not source._looks_like_job("https://www.computrabajo.com.co/ofertas-de-trabajo")
    assert source._is_manual_host("https://www.linkedin.com/jobs/view/123")
    assert source._is_manual_host("https://co.computrabajo.com/oferta/123")
    assert not source._looks_like_job("https://example.com/blog/python")


def test_import_url_endpoint_scores_the_job(monkeypatch):
    from app.api import routes

    payload = {
        "source": "testboard",
        "external_id": "import-test-1",
        "title": "Python Backend Engineer",
        "company": "Test Co",
        "description": "Python FastAPI SQL Docker remote in Colombia.",
        "location_text": "Remoto (Colombia)",
        "city": "",
        "country": "Colombia",
        "remote_type": "remote",
        "remote_scope": "colombia",
        "salary_min": 9000000,
        "salary_max": 14000000,
        "currency": "COP",
        "url": "https://example.com/jobs/import-test-1",
        "posted_at": "2026-10-20T10:00:00+00:00",
        "skills_required": ["Python", "FastAPI", "SQL", "Docker"],
        "skills_nice": [],
        "seniority": "mid",
        "years_experience": 0,
        "languages": {},
        "red_flags": [],
    }
    monkeypatch.setattr(routes, "import_job_from_url", lambda _url: (payload, "jsonld"))

    with TestClient(app) as client:
        assert client.post("/api/demo/seed").status_code == 200
        response = client.post(
            "/api/jobs/import-url",
            json={"url": "https://example.com/jobs/import-test-1"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
    assert data["extracted_with"] == "jsonld"
    assert data["job"]["title"] == "Python Backend Engineer"
    assert data["job"]["url"] == "https://example.com/jobs/import-test-1"
    assert data["job"]["match"]["eligible"] is True
    assert data["job"]["match"]["score"] > 0


def test_import_url_rejects_internal_targets():
    with TestClient(app) as client:
        assert client.post("/api/demo/seed").status_code == 200
        response = client.post("/api/jobs/import-url", json={"url": "http://127.0.0.1:8000/health"})

    assert response.status_code == 400
    assert "privadas" in response.json()["detail"].lower()


def test_link_only_payload_extracts_title_and_company_from_url():
    from app.services.job_import import link_only_payload

    payload = link_only_payload(
        "https://www.linkedin.com/jobs/view/backend-developer-at-acme-123456789",
        "Ingresa al portal para postularte.",
        "LinkedIn",
    )
    assert payload["title"] == "Backend Developer"
    assert payload["company"] == "Acme"
    assert payload["link_only"] is True
    assert payload["requires_login"] is True
    assert payload["url"].startswith("https://www.linkedin.com/")


def test_import_url_keeps_link_when_portal_requires_login(monkeypatch):
    from app.api import routes
    from app.services.job_import import JobLinkOnlyError

    def fake_import(url: str):
        raise JobLinkOnlyError("Ingresa al portal para postularte: requiere iniciar sesión.")

    monkeypatch.setattr(routes, "import_job_from_url", fake_import)
    with TestClient(app) as client:
        client.post("/api/demo/reset")
        response = client.post(
            "/api/jobs/import-url",
            json={"url": "https://www.linkedin.com/jobs/view/backend-developer-at-acme-123456789"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["link_only"] is True
        assert data["job"]["link_only"] is True
        assert data["job"]["requires_login"] is True
        assert "iniciar sesión" in data["message"].lower()

        jobs = client.get("/api/jobs?max_age_days=2").json()["items"]
        saved = next(item for item in jobs if item["id"] == data["job"]["id"])
        assert saved["requires_login"] is True
        assert saved["match"]["eligible"] is True
        client.post("/api/demo/reset")
