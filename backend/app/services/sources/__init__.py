from app.core.config import Settings
from app.services.sources.base import JobSource
from app.services.sources.demo import DemoSource
from app.services.sources.jooble import JoobleSource
from app.services.sources.jsearch import JSearchSource
from app.services.sources.remoteok import RemoteOKSource
from app.services.sources.remotive import RemotiveSource


def get_sources(settings: Settings) -> list[JobSource]:
    # Demo mode is fully offline: only the bundled dataset.
    if settings.demo_mode:
        return [DemoSource()]

    sources: list[JobSource] = []
    if settings.jsearch_configured:
        sources.append(JSearchSource(settings.jsearch_api_key))
    if settings.jooble_configured:
        sources.append(JoobleSource(settings.jooble_api_key))
    # Free remote sources always add variety, even without keys.
    sources.append(RemotiveSource())
    sources.append(RemoteOKSource())
    return sources
