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
