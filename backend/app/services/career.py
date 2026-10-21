"""Career search suggestions derived from a CV/profile.

The suggestions are intentionally editable: they only prefill the search
configuration, and the user can change roles or keywords in Settings.
"""

from __future__ import annotations

from app.models import Profile
from app.services.llm import llm_service
from app.services.matching import canonical_skill, role_family

FAMILY_ROLES: dict[str, tuple[tuple[str, str], ...]] = {
    "backend": (
        ("Backend Developer", "Desarrollador Backend"),
        ("Backend Engineer", "Ingeniero Backend"),
    ),
    "frontend": (
        ("Frontend Developer", "Desarrollador Frontend"),
        ("Frontend Engineer", "Ingeniero Frontend"),
    ),
    "fullstack": (
        ("Full Stack Developer", "Desarrollador Full Stack"),
        ("Full Stack Engineer", "Ingeniero Full Stack"),
    ),
    "data": (
        ("Data Analyst", "Analista de Datos"),
        ("Data Engineer", "Ingeniero de Datos"),
    ),
    "devops": (
        ("DevOps Engineer", "Ingeniero DevOps"),
        ("Site Reliability Engineer", "Ingeniero de Confiabilidad"),
    ),
    "mobile": (
        ("Mobile Developer", "Desarrollador Móvil"),
        ("Android Developer", "Desarrollador Android"),
        ("iOS Developer", "Desarrollador iOS"),
    ),
    "design": (
        ("Product Designer", "Diseñador de Producto"),
        ("UX Designer", "Diseñador UX"),
    ),
    "qa": (
        ("QA Engineer", "Ingeniero de QA"),
        ("Quality Assurance Engineer", "Ingeniero de Aseguramiento de Calidad"),
    ),
    "product": (
        ("Product Manager", "Gerente de Producto"),
        ("Product Owner", "Dueño de Producto"),
    ),
}

SKILL_ROLES: dict[str, tuple[str, str]] = {
    "python": ("Python Developer", "Desarrollador Python"),
    "java": ("Java Developer", "Desarrollador Java"),
    "javascript": ("JavaScript Developer", "Desarrollador JavaScript"),
    "typescript": ("TypeScript Developer", "Desarrollador TypeScript"),
    "react": ("React Developer", "Desarrollador React"),
    "node.js": ("Node.js Developer", "Desarrollador Node.js"),
    "node": ("Node.js Developer", "Desarrollador Node.js"),
    "django": ("Django Developer", "Desarrollador Django"),
    "fastapi": ("FastAPI Developer", "Desarrollador FastAPI"),
    "aws": ("AWS Engineer", "Ingeniero AWS"),
    "azure": ("Azure Engineer", "Ingeniero Azure"),
    "gcp": ("Cloud Engineer", "Ingeniero Cloud"),
    "sql": ("SQL Developer", "Desarrollador SQL"),
    "postgresql": ("PostgreSQL Developer", "Desarrollador PostgreSQL"),
    "flutter": ("Flutter Developer", "Desarrollador Flutter"),
    "react native": ("React Native Developer", "Desarrollador React Native"),
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = " ".join(str(value or "").split()).strip()
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def _role_families(profile: Profile) -> list[str]:
    texts = [profile.headline or ""]
    texts.extend(f"{item.get('role', '')} {item.get('company', '')}" for item in (profile.experience or []))
    families: list[str] = []
    for text in texts:
        family = role_family(text)
        if family and family not in families:
            families.append(family)
    return families


def heuristic_suggestions(profile: Profile) -> dict[str, list[str]]:
    years = int(profile.years_experience or 0)
    roles: list[str] = []
    for family in _role_families(profile):
        for english, spanish in FAMILY_ROLES.get(family, ()):
            if years <= 2:
                roles.extend([f"Junior {english}", f"{spanish} Junior"])
            elif years >= 6:
                roles.extend([f"Senior {english}", f"{spanish} Senior"])
            roles.extend([english, spanish])

    skills = [canonical_skill(str(skill)) for skill in (profile.skills or [])]
    for skill in skills:
        pair = SKILL_ROLES.get(skill.lower())
        if pair:
            roles.extend(pair)

    if not roles:
        headline = (profile.headline or "").strip()
        if headline:
            roles.append(headline)

    keywords = _dedupe(skills)[:15]
    return {"roles": _dedupe(roles)[:12], "keywords": keywords}


def suggest_search_preferences(profile: Profile, cv_text: str = "") -> dict[str, object]:
    heuristic = heuristic_suggestions(profile)
    llm_result = None
    if llm_service.configured:
        llm_result = llm_service.suggest_search_profile(profile.as_dict(), cv_text)
    llm_roles = []
    llm_keywords = []
    if isinstance(llm_result, dict):
        if isinstance(llm_result.get("roles"), list):
            llm_roles = [str(value) for value in llm_result["roles"] if str(value).strip()]
        if isinstance(llm_result.get("keywords"), list):
            llm_keywords = [str(value) for value in llm_result["keywords"] if str(value).strip()]
    roles = _dedupe(llm_roles + list(heuristic["roles"]))[:15]
    keywords = _dedupe(llm_keywords + list(heuristic["keywords"]))[:20]
    return {
        "roles": roles,
        "keywords": keywords,
        "source": "llm+heuristica" if llm_result else "heuristica",
    }
