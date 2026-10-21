from app.services.cv_parser import parse_profile_heuristic


def test_heuristic_parses_header_and_skills():
    text = """Camila Pérez
Bogotá, Colombia | camila@example.com | +57 300 123 4567
Backend Developer · Python · FastAPI · PostgreSQL
Resumen
Desarrolladora backend con 5 años de experiencia.
Habilidades: Python, FastAPI, PostgreSQL, Docker, AWS
"""
    profile = parse_profile_heuristic(text)

    assert profile["name"] == "Camila Pérez"
    assert profile["email"] == "camila@example.com"
    assert profile["headline"] == "Backend Developer · Python · FastAPI · PostgreSQL"
    assert "Python" in profile["skills"]
    assert "FastAPI" in profile["skills"]


def test_extract_languages_handles_parentheses_and_words():
    from app.services.cv_parser import extract_languages

    languages = extract_languages("Idiomas: Español (Nativo), Inglés (avanzado)")
    assert languages["Español"] == "Nativo"
    assert languages["Inglés"] == "C1"


def test_normalize_parsed_profile_handles_malformed_llm_output():
    from app.services.cv_parser import normalize_parsed_profile

    parsed = normalize_parsed_profile(
        {
            "name": "Ana",
            "skills": "Python, FastAPI",
            "experience": ["texto inválido", {"company": "Acme", "role": "Backend", "bullets": "API\nTesting"}],
            "education": ["texto inválido", {"institution": "UNAL", "degree": "Sistemas"}],
            "languages": ["Español: Nativo", "Inglés: B2"],
            "years_experience": "cuatro",
            "links": ["no es un objeto"],
        }
    )
    assert parsed["skills"] == ["Python", "FastAPI"]
    assert len(parsed["experience"]) == 1
    assert parsed["experience"][0]["bullets"] == ["API", "Testing"]
    assert parsed["languages"]["Inglés"] == "B2"
    assert parsed["years_experience"] == 0
    assert parsed["links"] == {}
