from app.services.search import normalize_job_data
from app.services.text_clean import clean_html_text


def test_clean_html_text_strips_tags_entities_and_mojibake():
    raw = '<h3>Desarrollador</h3><p>Empresa tecnolÃ³gica con soluciones sÃ³lidas &amp; reales.</p><ul><li>Python</li><li>FastAPI</li></ul>'
    clean = clean_html_text(raw)
    assert "<h3>" not in clean
    assert "<li>" not in clean
    assert "tecnológica" in clean
    assert "sólidas" in clean
    assert "&amp;" not in clean
    assert "Python" in clean


def test_normalize_job_data_cleans_description():
    normalized = normalize_job_data(
        {
            "title": "Backend Developer",
            "description": "<p>Buscamos perfil con <strong>Python</strong> y FastAPI.</p>",
            "url": "https://example.com/job",
        }
    )
    assert "<p>" not in normalized["description"]
    assert "<strong>" not in normalized["description"]
    assert "Python" in normalized["description"]
