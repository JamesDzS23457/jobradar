from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    skills: list[str] | None = None
    experience: list[dict[str, Any]] | None = None
    education: list[dict[str, Any]] | None = None
    languages: dict[str, str] | None = None
    links: dict[str, str] | None = None
    years_experience: int | None = Field(default=None, ge=0, le=60)


class PreferencesUpdate(BaseModel):
    roles: list[str] | None = None
    keywords: list[str] | None = None
    home_city: str | None = None
    commute_cities: list[str] | None = None
    country: str | None = None
    remote_preference: str | None = None
    accept_relocation: bool | None = None
    accept_international_remote: bool | None = None
    timezone: str | None = None
    salary_min: int | None = Field(default=None, ge=0)
    currency: str | None = None
    seniority: str | None = None
    contract_types: list[str] | None = None
    languages: dict[str, str] | None = None
    alert_threshold: int | None = Field(default=None, ge=0, le=100)
    digest_threshold: int | None = Field(default=None, ge=0, le=100)
    digest_hour: int | None = Field(default=None, ge=0, le=23)
    search_interval_hours: int | None = Field(default=None, ge=1, le=168)
    blacklist_companies: list[str] | None = None
    blacklist_keywords: list[str] | None = None
    freshness_days: int | None = Field(default=None, ge=1, le=365)
    auto_submit_enabled: bool | None = None
    auto_submit_max_per_run: int | None = Field(default=None, ge=1, le=20)
    default_cv_source: Literal["tailored", "original"] | None = None


class JobStatusUpdate(BaseModel):
    status: Literal["new", "saved", "dismissed", "applied", "discarded"]


class JobUrlImport(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


class ApplicationCreate(BaseModel):
    job_id: int
    status: Literal["applied", "interview", "offer", "rejected", "saved"] = "applied"
    notes: str = ""
    next_action_at: datetime | None = None
    cv_source: Literal["tailored", "original"] | None = None


class ApplicationUpdate(BaseModel):
    status: Literal["applied", "interview", "offer", "rejected", "saved"] | None = None
    notes: str | None = None
    next_action_at: datetime | None = None


class TailoredUpdate(BaseModel):
    content: dict[str, Any] | None = None
    approved: bool | None = None


class ApplicationSessionCreate(BaseModel):
    cv_source: Literal["tailored", "original"] | None = None


class DraftAnswersRequest(BaseModel):
    job_id: int
    questions: list[str] = Field(default_factory=list, max_length=30)


class SessionStatusUpdate(BaseModel):
    status: Literal["submitted", "manual", "failed", "awaiting_review", "queued"]
    message: str = ""


class AutoRunRequest(BaseModel):
    max_items: int | None = Field(default=None, ge=1, le=20)


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    score: float
    eligible: bool
    subscores: dict[str, float]
    reasons: list[str]
    gaps: list[str]
    red_flags: list[str]
    recommendation: str
    model: str


class JobSummary(BaseModel):
    id: int
    source: str
    title: str
    company: str
    location_text: str
    city: str
    country: str
    remote_type: str
    remote_scope: str
    salary_min: int | None
    salary_max: int | None
    currency: str
    url: str
    posted_at: datetime | None
    status: str
    skills_required: list[str]
    skills_nice: list[str]
    seniority: str
    years_experience: int
    languages: dict[str, str]
    red_flags: list[str]
    match: MatchOut | None = None


class JobDetail(JobSummary):
    description: str
