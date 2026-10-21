import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, Match, Preferences, Profile
from app.services.cv_parser import ALIASES
from app.services.language import infer_job_languages
from app.services.location import location_fit, seniority_from_title
from app.services.text_clean import clean_html_text

WEIGHTS = {
    "skills": 0.40,
    "title": 0.20,
    "seniority": 0.15,
    "location": 0.10,
    "language": 0.05,
    "salary": 0.05,
    "freshness": 0.05,
}

STOPWORDS = {
    "de",
    "del",
    "la",
    "las",
    "el",
    "los",
    "y",
    "en",
    "con",
    "para",
    "por",
    "a",
    "al",
    "the",
    "and",
    "of",
    "for",
    "in",
    "with",
    "at",
    "to",
    "an",
    "job",
    "role",
    "trabajo",
    "empleo",
}

ROLE_FAMILIES = {
    "backend": {"backend", "back-end", "back end", "server", "api", "microservices"},
    "frontend": {"frontend", "front-end", "front end", "react", "ui", "web"},
    "fullstack": {"fullstack", "full-stack", "full stack"},
    "data": {"data", "datos", "analytics", "analítica", "machine learning", "ml", "etl"},
    "devops": {"devops", "sre", "infrastructure", "cloud", "platform"},
    "mobile": {"mobile", "android", "ios", "flutter", "react native"},
    "design": {"design", "ux", "ui/ux", "product designer"},
}

SENIORITY_RANK = {"junior": 0, "mid": 1, "senior": 2, "lead": 3}

LEVELS = {
    "a1": 1,
    "a2": 2,
    "b1": 3,
    "b2": 4,
    "c1": 5,
    "c2": 6,
    "nativo": 6,
    "native": 6,
}


def canonical_skill(value: str) -> str:
    clean = value.strip().lower()
    return ALIASES.get(clean, value.strip())


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-záéíóúüñ0-9+#.]+", text.lower())
    return {word.strip(".") for word in words if word not in STOPWORDS and len(word) > 1}


def role_family(text: str) -> str:
    normalized = text.lower()
    for family, aliases in ROLE_FAMILIES.items():
        if any(alias in normalized for alias in aliases):
            return family
    return ""


def skill_score(profile_skills: list[str], required: list[str], nice: list[str]) -> tuple[float, list[str], list[str]]:
    profile = {canonical_skill(skill).lower() for skill in profile_skills}
    required_canonical = list(dict.fromkeys(canonical_skill(skill) for skill in required))
    nice_canonical = list(dict.fromkeys(canonical_skill(skill) for skill in nice))

    matched_required = [skill for skill in required_canonical if skill.lower() in profile]
    matched_nice = [skill for skill in nice_canonical if skill.lower() in profile]

    if required_canonical:
        required_ratio = len(matched_required) / len(required_canonical)
    else:
        required_ratio = 0.65

    if nice_canonical:
        nice_ratio = len(matched_nice) / len(nice_canonical)
    else:
        nice_ratio = 0.5

    score = required_ratio * 0.75 + nice_ratio * 0.25
    missing = [skill for skill in required_canonical if skill.lower() not in profile]
    return max(0.0, min(1.0, score)), matched_required, missing


def title_similarity(profile: Profile, job: Job) -> float:
    profile_text = " ".join([profile.headline, " ".join(profile.skills or []), profile.summary[:400]])
    profile_tokens = tokenize(profile_text)
    job_tokens = tokenize(job.title)
    if not profile_tokens or not job_tokens:
        return 0.5
    intersection = profile_tokens & job_tokens
    union = profile_tokens | job_tokens
    jaccard = len(intersection) / len(union) if union else 0.0
    profile_family = role_family(profile.headline)
    job_family = role_family(job.title)
    if profile_family and profile_family == job_family:
        return max(0.65, jaccard)
    return min(1.0, jaccard * 2.2)


def seniority_score(years: int, job: Job) -> float:
    required = job.years_experience or 0
    if required <= 0:
        required_by_label = {"junior": 0, "mid": 2, "senior": 5, "lead": 7}
        required = required_by_label.get(job.seniority, 2)
    if years >= required:
        over = years - required
        return 0.85 if over >= 6 else 1.0
    gap = required - years
    if gap <= 1:
        return 0.75
    if gap <= 2:
        return 0.5
    return 0.25


def language_key(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"english", "inglés", "ingles"}:
        return "inglés"
    if normalized in {"spanish", "español", "espanol"}:
        return "español"
    return normalized


def language_score(profile: Profile, job: Job, required: dict[str, str] | None = None) -> tuple[float, list[str]]:
    required = required if required is not None else _required_languages(job)
    if not required:
        return 1.0, []
    profile_languages = _profile_languages(profile)
    scores: list[float] = []
    gaps: list[str] = []
    for language, level in required.items():
        key = language_key(language)
        required_level = LEVELS.get(str(level).strip().lower(), 0)
        current_level = LEVELS.get(str(profile_languages.get(key, "")).strip().lower(), 0)
        if required_level <= 0:
            scores.append(0.7)
        elif current_level >= required_level:
            scores.append(1.0)
        elif current_level > 0:
            scores.append(0.5)
            gaps.append(f"{language} {level} requerido")
        else:
            scores.append(0.0)
            gaps.append(f"{language} {level} requerido")
    return sum(scores) / len(scores), gaps


def salary_score(prefs: Preferences, job: Job) -> float:
    if not prefs.salary_min or prefs.salary_min <= 0:
        return 0.6
    if job.salary_max is None and job.salary_min is None:
        return 0.6
    if job.currency and prefs.currency and job.currency.upper() != prefs.currency.upper():
        return 0.6
    salary_max = job.salary_max or job.salary_min or 0
    salary_min = job.salary_min or 0
    if salary_max >= prefs.salary_min:
        return 1.0
    if salary_min >= prefs.salary_min * 0.8:
        return 0.7
    return 0.3


def freshness_score(posted_at: datetime | None) -> float:
    if not posted_at:
        return 0.5
    now = datetime.now(UTC)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=UTC)
    days = max(0.0, (now - posted_at).total_seconds() / 86400)
    if days <= 3:
        return 1.0
    if days <= 7:
        return 0.8
    if days <= 14:
        return 0.6
    if days <= 30:
        return 0.3
    return 0.1


def recommendation_for(score: float) -> str:
    if score >= 85:
        return "Aplicar ya"
    if score >= 70:
        return "Buen match, revisar"
    if score >= 55:
        return "Vale la pena revisar"
    return "Match bajo"


def ineligible_match(job: Job, reason: str, recommendation: str = "No elegible") -> dict[str, Any]:
    return {
        "score": 0.0,
        "eligible": False,
        "subscores": {
            "skills": 0.0,
            "title": 0.0,
            "seniority": 0.0,
            "location": 0.0,
            "language": 0.0,
            "salary": 0.0,
            "freshness": 0.0,
        },
        "reasons": [reason],
        "gaps": [],
        "red_flags": job.red_flags or [],
        "recommendation": recommendation,
        "model": "heuristic",
    }


def _required_languages(job: Job) -> dict[str, str]:
    # Prefer explicit language requirements found in the text over legacy
    # stored values that may have been inferred too broadly.
    inferred = infer_job_languages(clean_html_text(f"{job.title}\n{job.description}"))
    if inferred:
        return inferred
    return job.languages if isinstance(job.languages, dict) else {}


def _profile_languages(profile: Profile) -> dict[str, str]:
    languages = profile.languages if isinstance(profile.languages, dict) else {}
    return {language_key(key): value for key, value in languages.items()}


def compute_match(profile: Profile, prefs: Preferences, job: Job) -> dict[str, Any]:
    location_value, eligible, location_reason = location_fit(job, prefs)

    if not eligible:
        return ineligible_match(job, location_reason, "No elegible por ubicación")

    required_languages = _required_languages(job)
    profile_languages = _profile_languages(profile)
    if profile_languages:
        for language, level in required_languages.items():
            required_level = LEVELS.get(str(level).strip().lower(), 0)
            current_level = LEVELS.get(str(profile_languages.get(language_key(language), "")).strip().lower(), 0)
            if required_level > 0 and current_level == 0:
                return ineligible_match(
                    job,
                    f"La vacante exige {language} {level} y tu CV no acredita ese idioma",
                    "No elegible por idioma",
                )

    preference_seniority = str(prefs.seniority or "any").lower()
    job_seniority = str(job.seniority or "").lower()
    title_seniority = seniority_from_title(job.title)
    if title_seniority != "mid":
        job_seniority = title_seniority
    if (
        preference_seniority in SENIORITY_RANK
        and job_seniority in SENIORITY_RANK
        and SENIORITY_RANK[job_seniority] > SENIORITY_RANK[preference_seniority]
    ):
        return ineligible_match(
            job,
            f"La vacante es {job_seniority} y tu búsqueda está configurada para {preference_seniority}",
            "No elegible por seniority",
        )

    skills_value, matched_skills, missing_skills = skill_score(
        profile.skills or [], job.skills_required or [], job.skills_nice or []
    )
    title_value = title_similarity(profile, job)
    seniority_value = seniority_score(profile.years_experience or 0, job)
    language_value, language_gaps = language_score(profile, job, required_languages)
    salary_value = salary_score(prefs, job)
    freshness_value = freshness_score(job.posted_at)

    subscores = {
        "skills": round(skills_value * 100, 1),
        "title": round(title_value * 100, 1),
        "seniority": round(seniority_value * 100, 1),
        "location": round(location_value * 10, 1),
        "language": round(language_value * 100, 1),
        "salary": round(salary_value * 100, 1),
        "freshness": round(freshness_value * 100, 1),
    }

    total = sum(
        {
            "skills": skills_value,
            "title": title_value,
            "seniority": seniority_value,
            "location": location_value / 10,
            "language": language_value,
            "salary": salary_value,
            "freshness": freshness_value,
        }[key]
        * weight
        for key, weight in WEIGHTS.items()
    )
    score = round(max(0.0, min(100.0, total * 100)), 1)

    reasons: list[str] = [location_reason]
    if job.skills_required:
        reasons.append(f"Coincides en {len(matched_skills)} de {len(job.skills_required)} skills obligatorios")
    if title_value >= 0.65:
        reasons.append("El rol y el título están alineados con tu perfil")
    if seniority_value >= 0.75:
        reasons.append("Tu experiencia encaja con el seniority pedido")
    if language_value >= 0.9:
        reasons.append("Cumples los idiomas requeridos")
    if salary_value >= 0.9:
        reasons.append("El salario está dentro de tu expectativa")

    gaps = [f"Falta {skill}" for skill in missing_skills[:6]]
    gaps.extend(language_gaps)
    if profile.years_experience < (job.years_experience or 0):
        gaps.append(f"Piden {job.years_experience}+ años y tu perfil tiene {profile.years_experience}")

    return {
        "score": score,
        "eligible": True,
        "subscores": subscores,
        "reasons": reasons[:5],
        "gaps": gaps[:6],
        "red_flags": job.red_flags or [],
        "recommendation": recommendation_for(score),
        "model": "heuristic",
    }


def upsert_match(db: Session, job: Job, result: dict[str, Any]) -> Match:
    match = job.match
    if match is None:
        match = Match(job_id=job.id)
        db.add(match)
    match.score = float(result["score"])
    match.eligible = bool(result["eligible"])
    match.subscores = result["subscores"]
    match.reasons = result["reasons"]
    match.gaps = result["gaps"]
    match.red_flags = result["red_flags"]
    match.recommendation = result["recommendation"]
    match.model = result["model"]
    match.profile_version = 1
    return match


def recompute_all(db: Session, profile: Profile, prefs: Preferences) -> int:
    jobs = db.scalars(select(Job)).all()
    for job in jobs:
        result = compute_match(profile, prefs, job)
        upsert_match(db, job, result)
    db.commit()
    return len(jobs)


def match_to_dict(match: Match | None) -> dict[str, Any] | None:
    if match is None:
        return None
    return {
        "id": match.id,
        "score": match.score,
        "eligible": match.eligible,
        "subscores": match.subscores,
        "reasons": match.reasons,
        "gaps": match.gaps,
        "red_flags": match.red_flags,
        "recommendation": match.recommendation,
        "model": match.model,
    }
