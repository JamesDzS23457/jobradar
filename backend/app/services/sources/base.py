from abc import ABC, abstractmethod
from typing import Any

from app.models import Preferences


class JobSource(ABC):
    name = "base"

    @abstractmethod
    def fetch(self, prefs: Preferences) -> list[dict[str, Any]]:
        raise NotImplementedError
