from app.models import Profile
from app.services.career import heuristic_suggestions, suggest_search_preferences


def profile() -> Profile:
    return Profile(
        name="Ana Torres",
        headline="Backend Developer · Python · FastAPI · AWS",
        skills=["Python", "FastAPI", "PostgreSQL", "AWS", "Docker"],
        experience=[{"company": "FinTech", "role": "Backend Developer", "bullets": []}],
        years_experience=4,
    )


def test_heuristic_suggestions_include_spanish_and_english_roles():
    suggestions = heuristic_suggestions(profile())
    roles = [role.lower() for role in suggestions["roles"]]
    assert "backend developer" in roles
    assert "desarrollador backend" in roles
    assert "python developer" in roles
    assert "desarrollador python" in roles
    assert "Python" in suggestions["keywords"]


def test_suggestions_are_editable_lists_and_do_not_duplicate():
    suggestions = suggest_search_preferences(profile(), "Backend Developer con Python")
    assert isinstance(suggestions["roles"], list)
    assert isinstance(suggestions["keywords"], list)
    assert len(suggestions["roles"]) == len(set(role.lower() for role in suggestions["roles"]))
