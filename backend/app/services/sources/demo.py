import json
from pathlib import Path
from typing import Any

from app.models import Preferences
from app.services.sources.base import JobSource

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "demo_jobs.json"


class DemoSource(JobSource):
    name = "demo"

    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
