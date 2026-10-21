from app.core.config import Settings
from app.services.sources import get_sources
from app.services.sources.tavily import TavilySearchSource


def test_tavily_extracts_result_urls():
    payload = {
        "results": [
            {"url": "https://www.computrabajo.com.co/oferta/1", "title": "Backend"},
            {"url": "https://www.elempleo.com/co/ofertas-empleo/2", "title": "Data"},
            {"title": "sin url"},
        ]
    }
    assert TavilySearchSource._result_urls(payload) == [
        "https://www.computrabajo.com.co/oferta/1",
        "https://www.elempleo.com/co/ofertas-empleo/2",
    ]


def test_tavily_keyless_is_enabled_without_api_key():
    settings = Settings(
        demo_mode=False,
        web_search_provider="tavily",
        tavily_api_key="",
        tavily_keyless=True,
        jsearch_api_key="",
        jooble_api_key="",
        brave_search_api_key="",
    )
    names = [source.name for source in get_sources(settings)]
    assert "tavily" in names
    assert "websearch" not in names


def test_brave_provider_requires_key():
    settings = Settings(
        demo_mode=False,
        web_search_provider="brave",
        tavily_keyless=True,
        brave_search_api_key="",
        jsearch_api_key="",
        jooble_api_key="",
    )
    names = [source.name for source in get_sources(settings)]
    assert "websearch" not in names
    assert "tavily" not in names
