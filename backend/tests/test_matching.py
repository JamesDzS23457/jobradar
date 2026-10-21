from datetime import UTC, datetime

from app.models import Job, Preferences, Profile
from app.services.matching import compute_match


def profile() -> Profile:
    return Profile(
        name="Ana Torres",
        headline="Backend Developer · Python · FastAPI · AWS",
        summary="Backend con experiencia en APIs y servicios en la nube.",
        skills=["Python", "FastAPI", "PostgreSQL", "AWS", "Docker", "Redis"],
        experience=[
            {
                "company": "FinTech",
                "role": "Backend Developer",
                "dates": "2022 - 2025",
                "bullets": ["APIs con FastAPI y PostgreSQL"],
            }
        ],
        languages={"Español": "Nativo", "Inglés": "B2"},
        years_experience=4,
    )


def prefs() -> Preferences:
    return Preferences(
        home_city="Bogotá",
        commute_cities=["Chía"],
        accept_relocation=False,
        accept_international_remote=True,
        salary_min=9000000,
        currency="COP",
    )


def job(**overrides) -> Job:
    data = {
        "title": "Senior Backend Engineer (Python)",
        "company": "Rappi",
        "location_text": "Bogotá, Colombia",
        "city": "Bogotá",
        "country": "Colombia",
        "remote_type": "hybrid",
        "remote_scope": "national",
        "skills_required": ["Python", "FastAPI", "PostgreSQL", "AWS", "Docker"],
        "skills_nice": ["Redis", "Kubernetes"],
        "seniority": "senior",
        "years_experience": 5,
        "languages": {"Español": "B2", "Inglés": "B2"},
        "salary_min": 14000000,
        "salary_max": 20000000,
        "currency": "COP",
        "posted_at": datetime.now(UTC),
    }
    data.update(overrides)
    return Job(**data)


def test_high_match_for_aligned_role():
    result = compute_match(profile(), prefs(), job())
    assert result["eligible"] is True
    assert result["score"] >= 70
    assert result["subscores"]["skills"] >= 80


def test_location_exclusion_wins():
    result = compute_match(profile(), prefs(), job(city="Medellín", location_text="Medellín, Colombia"))
    assert result["eligible"] is False
    assert result["score"] == 0
    assert "Medellín" in result["reasons"][0]


def test_low_match_for_unrelated_stack():
    result = compute_match(
        profile(),
        prefs(),
        job(
            title="Ruby on Rails Engineer",
            skills_required=["Ruby", "Rails", "PostgreSQL", "Redis"],
            skills_nice=["Kubernetes"],
        ),
    )
    assert result["eligible"] is True
    assert result["score"] < 70


def test_spanish_only_profile_excludes_english_required_job():
    spanish_only = profile()
    spanish_only.languages = {"Español": "Nativo"}
    result = compute_match(spanish_only, prefs(), job(languages={"Inglés": "B2"}))
    assert result["eligible"] is False
    assert "idioma" in result["recommendation"].lower()


def test_english_not_required_when_description_says_it_is_a_plus():
    spanish_only = profile()
    spanish_only.languages = {"Español": "Nativo"}
    result = compute_match(
        spanish_only,
        prefs(),
        job(languages={}, description="English is a plus. Trabajo backend con Python."),
    )
    assert result["eligible"] is True


def test_infer_job_languages_handles_explicit_and_optional_requirements():
    from app.services.language import infer_job_languages

    assert infer_job_languages("Requisitos: Inglés B2 obligatorio.") == {"Inglés": "B2"}
    assert infer_job_languages("English is a plus, no es obligatorio.") == {}
