import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Stage(str, enum.Enum):
    saved = "saved"
    applied = "applied"
    recruiter_screen = "recruiter_screen"
    assessment = "assessment"
    technical = "technical"
    final = "final"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class RecruiterStatus(str, enum.Enum):
    to_contact = "to_contact"
    contacted = "contacted"
    replied = "replied"
    referral_requested = "referral_requested"
    referred = "referred"
    no_response = "no_response"


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class PracticeStatus(str, enum.Enum):
    todo = "todo"
    attempted = "attempted"
    solved = "solved"
    mastered = "mastered"


class Profile(Base):
    """Single-row table holding the job seeker's targets. Drives matching and weekly goals."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    target_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    open_to_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    salary_expectation: Mapped[str] = mapped_column(String(80), default="")
    weekly_application_goal: Mapped[int] = mapped_column(Integer, default=25)
    weekly_dsa_goal: Mapped[int] = mapped_column(Integer, default=15)
    weekly_outreach_goal: Mapped[int] = mapped_column(Integer, default=10)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200), index=True)
    location: Mapped[str] = mapped_column(String(200), default="")
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    salary: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    posted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)

    match_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    matched_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, default=list)

    application: Mapped["Application | None"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def application_id(self) -> int | None:
        return self.application.id if self.application else None

    @property
    def application_stage(self) -> "Stage | None":
        return self.application.stage if self.application else None


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    stage: Mapped[Stage] = mapped_column(Enum(Stage, native_enum=False), default=Stage.saved)
    applied_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_follow_up: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    referral: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    job: Mapped[Job] = relationship(back_populates="application")
    events: Mapped[list["StageEvent"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="StageEvent.at"
    )


class StageEvent(Base):
    """Audit trail of stage transitions; powers the funnel and weekly activity numbers."""

    __tablename__ = "stage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    from_stage: Mapped[Stage | None] = mapped_column(Enum(Stage, native_enum=False), nullable=True)
    to_stage: Mapped[Stage] = mapped_column(Enum(Stage, native_enum=False))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="events")


class Recruiter(Base):
    __tablename__ = "recruiters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    company: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    linkedin_url: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[RecruiterStatus] = mapped_column(
        Enum(RecruiterStatus, native_enum=False), default=RecruiterStatus.to_contact
    )
    last_contacted: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_follow_up: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DSAProblem(Base):
    __tablename__ = "dsa_problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), unique=True)
    url: Mapped[str] = mapped_column(String(300), default="")
    topic: Mapped[str] = mapped_column(String(60), index=True)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, native_enum=False))
    status: Mapped[PracticeStatus] = mapped_column(
        Enum(PracticeStatus, native_enum=False), default=PracticeStatus.todo
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    review_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class PrepQuestion(Base):
    __tablename__ = "prep_questions"
    __table_args__ = (UniqueConstraint("track", "question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    track: Mapped[str] = mapped_column(String(40), index=True)
    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(20), default="seed")
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    review_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)


class PracticeLog(Base):
    """One row per DSA attempt or prep review; used for streaks and weekly goals."""

    __tablename__ = "practice_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # "dsa" | "prep"
    item_id: Mapped[int] = mapped_column(Integer)
    quality: Mapped[int] = mapped_column(Integer)
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class JobSource(Base):
    """A saved feed: a company careers board or a search, re-run on refresh."""

    __tablename__ = "job_sources"
    __table_args__ = (UniqueConstraint("kind", "query", "location"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # greenhouse | lever | ashby | adzuna | remotive
    query: Mapped[str] = mapped_column(String(200))  # company slug or search keywords
    location: Mapped[str] = mapped_column(String(120), default="")
    company_name: Mapped[str] = mapped_column(String(200), default="")
    title_keywords: Mapped[str] = mapped_column(String(500), default="")
    location_keywords: Mapped[str] = mapped_column(String(500), default="")
    limit: Mapped[int] = mapped_column(Integer, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_found: Mapped[int] = mapped_column(Integer, default=0)
    last_created: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
