from app.models import Job, Preferences
from app.services.location import location_fit


def make_job(**overrides) -> Job:
    data = {
        "title": "Backend Developer",
        "company": "Demo",
        "location_text": "Bogotá, Colombia",
        "city": "Bogotá",
        "country": "Colombia",
        "remote_type": "hybrid",
        "remote_scope": "national",
    }
    data.update(overrides)
    return Job(**data)


def make_prefs(**overrides) -> Preferences:
    data = {
        "home_city": "Bogotá",
        "commute_cities": ["Chía", "Cota", "Soacha"],
        "country": "Colombia",
        "accept_relocation": False,
        "accept_international_remote": True,
    }
    data.update(overrides)
    return Preferences(**data)


def test_bogota_hybrid_is_eligible():
    score, eligible, reason = location_fit(make_job(), make_prefs())
    assert eligible is True
    assert score == 10.0
    assert "Bogotá" in reason


def test_nearby_city_is_eligible():
    job = make_job(city="Chía", location_text="Chía, Cundinamarca, Colombia")
    score, eligible, _ = location_fit(job, make_prefs())
    assert eligible is True
    assert score == 9.0


def test_other_colombian_city_requires_relocation():
    job = make_job(city="Medellín", location_text="Medellín, Colombia")
    score, eligible, _ = location_fit(job, make_prefs())
    assert eligible is False
    assert score == 0.0


def test_remote_colombia_is_eligible():
    job = make_job(
        city="",
        location_text="Remoto - Colombia",
        country="Colombia",
        remote_type="remote",
        remote_scope="colombia",
    )
    score, eligible, _ = location_fit(job, make_prefs())
    assert eligible is True
    assert score == 9.0


def test_remote_global_is_eligible():
    job = make_job(
        city="",
        location_text="Remote - Worldwide",
        country="Worldwide",
        remote_type="remote",
        remote_scope="global",
    )
    score, eligible, _ = location_fit(job, make_prefs())
    assert eligible is True
    assert score == 7.0


def test_us_only_remote_is_not_eligible():
    job = make_job(
        city="",
        location_text="Remote - US only",
        country="United States",
        remote_type="remote",
        remote_scope="us_only",
    )
    score, eligible, _ = location_fit(job, make_prefs())
    assert eligible is False
    assert score == 0.0


def test_onsite_outside_colombia_is_not_eligible():
    job = make_job(
        city="Seattle",
        location_text="Seattle, United States",
        country="United States",
        remote_type="onsite",
    )
    score, eligible, _ = location_fit(job, make_prefs())
    assert eligible is False
    assert score == 0.0
