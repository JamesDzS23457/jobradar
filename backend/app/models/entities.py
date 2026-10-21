from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    location: Mapped[str] = mapped_column(String(120), default="Bogotá, Colombia")
    headline: Mapped[str] = mapped_column(String(220), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    experience: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    education: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    languages: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    links: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    raw_cv_text: Mapped[str] = mapped_column(Text, default="")
    cv_file_path: Mapped[str] = mapped_column(String(500), default="")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "headline": self.headline,
            "summary": self.summary,
            "skills": self.skills or [],
            "experience": self.experience or [],
            "education": self.education or [],
            "languages": self.languages or {},
            "links": self.links or {},
            "years_experience": self.years_experience,
            "updated_at": self.updated_at,
        }


class Preferences(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    home_city: Mapped[str] = mapped_column(String(120), default="Bogotá")
    commute_cities: Mapped[list[str]] = mapped_column(JSON, default=list)
    country: Mapped[str] = mapped_column(String(80), default="Colombia")
    remote_preference: Mapped[str] = mapped_column(String(30), default="any")
    accept_relocation: Mapped[bool] = mapped_column(Boolean, default=False)
    accept_international_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(80), default="America/Bogota")
    salary_min: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="COP")
    seniority: Mapped[str] = mapped_column(String(30), default="mid")
    contract_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    languages: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    alert_threshold: Mapped[int] = mapped_column(Integer, default=85)
    digest_threshold: Mapped[int] = mapped_column(Integer, default=70)
    digest_hour: Mapped[int] = mapped_column(Integer, default=8)
    search_interval_hours: Mapped[int] = mapped_column(Integer, default=6)
    blacklist_companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    blacklist_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    freshness_days: Mapped[int] = mapped_column(Integer, default=2)
    auto_submit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_submit_max_per_run: Mapped[int] = mapped_column(Integer, default=5)
    default_cv_source: Mapped[str] = mapped_column(String(20), default="tailored")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "roles": self.roles or [],
            "keywords": self.keywords or [],
            "home_city": self.home_city,
            "commute_cities": self.commute_cities or [],
            "country": self.country,
            "remote_preference": self.remote_preference,
            "accept_relocation": self.accept_relocation,
            "accept_international_remote": self.accept_international_remote,
            "timezone": self.timezone,
            "salary_min": self.salary_min,
            "currency": self.currency,
            "seniority": self.seniority,
            "contract_types": self.contract_types or [],
            "languages": self.languages or {},
            "alert_threshold": self.alert_threshold,
            "digest_threshold": self.digest_threshold,
            "digest_hour": self.digest_hour,
            "search_interval_hours": self.search_interval_hours,
            "blacklist_companies": self.blacklist_companies or [],
            "blacklist_keywords": self.blacklist_keywords or [],
            "freshness_days": self.freshness_days or 2,
            "auto_submit_enabled": bool(self.auto_submit_enabled),
            "auto_submit_max_per_run": self.auto_submit_max_per_run or 5,
            "default_cv_source": self.default_cv_source or "tailored",
            "updated_at": self.updated_at,
        }


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("hash", name="uq_jobs_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), default="demo")
    external_id: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(240), default="")
    company: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    location_text: Mapped[str] = mapped_column(String(240), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    remote_type: Mapped[str] = mapped_column(String(30), default="unknown")
    remote_scope: Mapped[str] = mapped_column(String(30), default="unknown")
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="COP")
    url: Mapped[str] = mapped_column(String(700), default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    hash: Mapped[str] = mapped_column(String(64), default="")
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="new")
    imported_manually: Mapped[bool] = mapped_column(Boolean, default=False)
    link_only: Mapped[bool] = mapped_column(Boolean, default=False)
    collector: Mapped[str] = mapped_column(String(50), default="")
    skills_required: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills_nice: Mapped[list[str]] = mapped_column(JSON, default=list)
    seniority: Mapped[str] = mapped_column(String(30), default="mid")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    languages: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    red_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    match: Mapped["Match | None"] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")
    application: Mapped["Application | None"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("job_id", name="uq_matches_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    score: Mapped[float] = mapped_column(Float, default=0)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    subscores: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    gaps: Mapped[list[str]] = mapped_column(JSON, default=list)
    red_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommendation: Mapped[str] = mapped_column(String(240), default="")
    model: Mapped[str] = mapped_column(String(80), default="heuristic")
    fit_level: Mapped[str] = mapped_column(String(20), default="exact")
    stretch_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="match")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", name="uq_applications_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="applied")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cv_source: Mapped[str] = mapped_column(String(20), default="tailored")
    cv_file_name: Mapped[str] = mapped_column(String(300), default="")
    portal_mode: Mapped[str] = mapped_column(String(30), default="manual_only")
    application_url: Mapped[str] = mapped_column(String(700), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[Job] = relationship(back_populates="application")


class ApplicationRun(Base):
    __tablename__ = "application_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="running")
    max_items: Mapped[int] = mapped_column(Integer, default=5)
    total: Mapped[int] = mapped_column(Integer, default=0)
    submitted: Mapped[int] = mapped_column(Integer, default=0)
    manual: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplicationRunItem(Base):
    __tablename__ = "application_run_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("application_runs.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_sessions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="queued")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[Job] = relationship()


class ApplicationSession(Base):
    __tablename__ = "application_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="awaiting_review")
    portal_mode: Mapped[str] = mapped_column(String(30), default="assisted")
    cv_source: Mapped[str] = mapped_column(String(20), default="tailored")
    cv_file_name: Mapped[str] = mapped_column(String(300), default="")
    cv_path: Mapped[str] = mapped_column(String(700), default="")
    fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[Job] = relationship()


class TailoredCV(Base):
    __tablename__ = "tailored_cvs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    docx_path: Mapped[str] = mapped_column(String(500), default="")
    pdf_path: Mapped[str] = mapped_column(String(500), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship()


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[str] = mapped_column(String(30), default="email")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(30), default="sent")
    error: Mapped[str] = mapped_column(Text, default="")


class SearchRun(Base):
    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    found: Mapped[int] = mapped_column(Integer, default=0)
    new: Mapped[int] = mapped_column(Integer, default=0)
    sources: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(30), default="")
    reason: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
