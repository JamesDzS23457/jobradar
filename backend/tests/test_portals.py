from app.core.config import Settings
from app.services.portals import classify_portal


def test_manual_only_portals_are_never_assisted():
    settings = Settings()
    for url in (
        "https://www.linkedin.com/jobs/view/123",
        "https://co.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-backend",
        "https://www.elempleo.com/co/ofertas-empleo/backend",
        "https://www.magneto.com.co/oferta/123",
        "https://www.indeed.com/viewjob?jk=123",
        "https://www.glassdoor.com/job-listing/123",
    ):
        portal = classify_portal(url, settings)
        assert portal.mode == "manual_only"
        assert portal.can_assist is False
        assert portal.can_auto_submit is False


def test_ats_allowlist_supports_auto_submit():
    settings = Settings()
    portal = classify_portal("https://boards.greenhouse.io/acme/jobs/123", settings)
    assert portal.mode == "auto_submit"
    assert portal.can_assist is True
    assert portal.can_auto_submit is True


def test_unknown_portal_is_assisted_but_never_auto_submit():
    portal = classify_portal("https://careers.example-company.com/apply/backend", Settings())
    assert portal.mode == "assisted"
    assert portal.can_assist is True
    assert portal.can_auto_submit is False


def test_empty_url_is_manual():
    portal = classify_portal("", Settings())
    assert portal.mode == "manual_only"
    assert portal.can_assist is False
