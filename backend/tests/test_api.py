from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        root_health = client.get("/health")
        assert root_health.status_code == 200
        assert root_health.json()["status"] == "ok"


def test_demo_seed_and_dashboard():
    with TestClient(app) as client:
        seed = client.post("/api/demo/seed")
        assert seed.status_code == 200

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        payload = dashboard.json()
        assert payload["profile_complete"] is True
        assert payload["stats"]["total_jobs"] > 0
        assert len(payload["top_matches"]) > 0

        jobs = client.get("/api/jobs")
        assert jobs.status_code == 200
        assert jobs.json()["total"] > 0
        assert all(item["match"]["eligible"] for item in jobs.json()["items"])


def test_tailor_and_download():
    with TestClient(app) as client:
        client.post("/api/demo/seed")
        jobs = client.get("/api/jobs").json()["items"]
        job_id = jobs[0]["id"]
        tailored = client.post(f"/api/jobs/{job_id}/tailor")
        assert tailored.status_code == 200
        tailored_id = tailored.json()["tailored"]["id"]
        assert tailored.json()["tailored"]["content"]["summary"]

        blocked = client.get(f"/api/tailored/{tailored_id}/download?format=docx")
        assert blocked.status_code == 403

        approved = client.put(f"/api/tailored/{tailored_id}", json={"approved": True})
        assert approved.status_code == 200

        docx = client.get(f"/api/tailored/{tailored_id}/download?format=docx")
        assert docx.status_code == 200
        assert docx.content[:2] == b"PK"


def test_saving_does_not_override_applied_status():
    with TestClient(app) as client:
        client.post("/api/demo/reset")
        job = client.get("/api/jobs").json()["items"][0]
        created = client.post(
            "/api/applications",
            json={"job_id": job["id"], "status": "applied"},
        )
        assert created.status_code == 200

        updated = client.patch(f"/api/jobs/{job['id']}", json={"status": "saved"})
        assert updated.status_code == 200
        assert updated.json()["job"]["status"] == "applied"

        applications = client.get("/api/applications").json()["items"]
        application = next(item for item in applications if item["job_id"] == job["id"])
        assert application["status"] == "applied"

