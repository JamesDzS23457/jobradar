from datetime import UTC, datetime, timedelta

from app.services.sources.jsearch import JSearchSource, _parse_posted_at


def test_jsearch_extracts_v2_jobs_dict():
    payload = {
        "status": "OK",
        "data": {
            "jobs": [
                {"job_id": "1", "job_title": "Backend Developer"},
                {"job_id": "2", "job_title": "Platform Engineer"},
            ]
        },
    }
    assert len(JSearchSource._extract_items(payload)) == 2


def test_jsearch_supports_legacy_list_shape():
    payload = {"data": [{"job_id": "1"}]}
    assert JSearchSource._extract_items(payload) == [{"job_id": "1"}]


def test_jsearch_normalizes_v2_location_and_relative_date():
    source = JSearchSource("test-key")
    item = {
        "job_id": "abc",
        "job_title": "Backend Developer",
        "employer_name": "Acme",
        "job_location": "Bogotá     •  a través de LinkedIn",
        "job_posted_at": "hace 5 días",
        "job_apply_link": "https://example.com/job",
        "job_description": "Python y FastAPI",
    }
    normalized = source._normalize(item)
    assert normalized["location_text"] == "Bogotá"
    assert normalized["city"] == "Bogotá"
    assert normalized["country"] == "Colombia"
    assert normalized["posted_at"] is not None
    assert normalized["url"] == "https://example.com/job"


def test_jsearch_parses_relative_dates():
    now = datetime.now(UTC)
    parsed = _parse_posted_at({"job_posted_at": "hace 2 horas"})
    assert parsed is not None
    assert abs((now - parsed) - timedelta(hours=2)) < timedelta(seconds=10)


def test_jsearch_parses_iso_dates():
    parsed = _parse_posted_at({"job_posted_at_datetime_utc": "2026-10-20T12:00:00Z"})
    assert parsed == datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def test_normalize_job_data_does_not_treat_english_plus_as_requirement():
    from app.services.search import normalize_job_data

    optional = normalize_job_data(
        {"title": "Backend Developer", "description": "English is a plus. Python y FastAPI.", "url": "https://example.com/1"}
    )
    required = normalize_job_data(
        {"title": "Backend Developer", "description": "English B2 is required. Python y FastAPI.", "url": "https://example.com/2"}
    )
    assert optional["languages"] == {}
    assert required["languages"] == {"Inglés": "B2"}
