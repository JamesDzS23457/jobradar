from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.main import app
from app.services import emailer


def test_digest_sends_once(monkeypatch):
    with TestClient(app) as client:
        assert client.post("/api/demo/seed").status_code == 200

    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_user", "alerts@example.com")
    monkeypatch.setattr(settings, "smtp_password", "app-password")

    sent: dict[str, str] = {}

    def fake_send(settings, subject, body, to=None):
        sent["subject"] = subject
        sent["body"] = body
        return True, ""

    monkeypatch.setattr(emailer, "_send", fake_send)

    db = SessionLocal()
    try:
        first = emailer.send_digest(db, settings)
        second = emailer.send_digest(db, settings)
    finally:
        db.close()

    assert first > 0
    assert "vacantes para revisar" in sent["subject"]
    assert "Ver vacante" in sent["body"]
    assert second == 0
