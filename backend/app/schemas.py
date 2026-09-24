from datetime import date, datetime, timezone
from typing import Annotated, Literal, get_args

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.database.models import Difficulty, PracticeStatus, RecruiterStatus, Stage

Track = Literal["python", "sql", "backend", "genai", "system-design"]
PREP_TRACKS: tuple[str, ...] = get_args(Track)

# SQLite drops tzinfo; timestamps are always stored in UTC, so label them as such.
UTCDateTime = Annotated[datetime, AfterValidator(lambda d: d if d.tzinfo else d.replace(tzinfo=timezone.utc))]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- profile


class ProfileBase(BaseModel):
    name: str = ""
    target_roles: list[str] = []
    locations: list[str] = []
    open_to_remote: bool = True
    skills: list[str] = []
    experience_years: float = Field(0, ge=0, le=50)
    salary_expectation: str = ""
    weekly_application_goal: int = Field(25, ge=0, le=500)
    weekly_dsa_goal: int = Field(15, ge=0, le=500)
    weekly_outreach_goal: int = Field(10, ge=0, le=500)


class ProfileRead(ProfileBase, ORM):
    pass


# ---------------------------------------------------------------- jobs


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    location: str = ""
    remote: bool = False
    salary: str = ""
    url: str = ""
    description: str = ""
    tags: list[str] = []
    external_id: str | None = None
    posted_at: date | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    remote: bool | None = None
    salary: str | None = None
    url: str | None = None
    description: str | None = None
    archived: bool | None = None


class JobRead(ORM):
    id: int
    title: str
    company: str
    location: str
    remote: bool
    salary: str
    url: str
    description: str
    skills: list[str]
    source: str
    posted_at: date | None
    created_at: UTCDateTime
    archived: bool
    match_score: float | None
    matched_skills: list[str]
    missing_skills: list[str]
    application_id: int | None = None
    application_stage: Stage | None = None


class JobSummary(ORM):
    id: int
    title: str
    company: str
    location: str
    remote: bool
    salary: str
    url: str
    match_score: float | None


class IngestResponse(BaseModel):
    created: int
    duplicates: int
    created_ids: list[int]


SourceKind = Literal["greenhouse", "lever", "ashby", "adzuna", "remotive"]


class JobSourceCreate(BaseModel):
    """Either paste a careers-page URL, or give kind + query (slug / search keywords)."""

    url: str = ""
    kind: SourceKind | None = None
    query: str = Field("", max_length=200)
    location: str = Field("", max_length=120)
    company_name: str = Field("", max_length=200)
    title_keywords: str = Field("", max_length=500)
    location_keywords: str = Field("", max_length=500)
    limit: int = Field(100, ge=1, le=500)


class JobSourceUpdate(BaseModel):
    company_name: str | None = None
    title_keywords: str | None = None
    location_keywords: str | None = None
    limit: int | None = Field(None, ge=1, le=500)
    enabled: bool | None = None


class JobSourceRead(ORM):
    id: int
    kind: SourceKind
    query: str
    location: str
    company_name: str
    title_keywords: str
    location_keywords: str
    limit: int
    enabled: bool
    last_run_at: UTCDateTime | None
    last_found: int
    last_created: int
    last_error: str


class SourceRunResult(BaseModel):
    source: JobSourceRead
    found: int
    created: int
    duplicates: int


# ---------------------------------------------------------------- matching


class AnalyzeRequest(BaseModel):
    title: str = ""
    description: str = Field(min_length=1)
    location: str = ""


class AnalyzeResponse(BaseModel):
    score: float
    skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    reasons: list[str]


class SkillGap(BaseModel):
    skill: str
    jobs: int
    track: str | None


# ---------------------------------------------------------------- applications


class ApplicationCreate(BaseModel):
    job_id: int | None = None
    job: JobCreate | None = None
    stage: Stage = Stage.applied
    applied_on: date | None = None
    next_follow_up: date | None = None
    referral: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _job_reference(self):
        if (self.job_id is None) == (self.job is None):
            raise ValueError("Provide exactly one of job_id or job")
        return self


class ApplicationUpdate(BaseModel):
    stage: Stage | None = None
    applied_on: date | None = None
    next_follow_up: date | None = None
    referral: bool | None = None
    notes: str | None = None


class StageEventRead(ORM):
    from_stage: Stage | None
    to_stage: Stage
    at: UTCDateTime


class ApplicationRead(ORM):
    id: int
    stage: Stage
    applied_on: date | None
    next_follow_up: date | None
    referral: bool
    notes: str
    created_at: UTCDateTime
    updated_at: datetime
    job: JobSummary
    events: list[StageEventRead]


# ---------------------------------------------------------------- recruiters


class RecruiterBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company: str = ""
    title: str = ""
    email: str = ""
    linkedin_url: str = ""
    status: RecruiterStatus = RecruiterStatus.to_contact
    last_contacted: date | None = None
    next_follow_up: date | None = None
    notes: str = ""


class RecruiterUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    title: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    status: RecruiterStatus | None = None
    last_contacted: date | None = None
    next_follow_up: date | None = None
    notes: str | None = None


class RecruiterRead(RecruiterBase, ORM):
    id: int
    created_at: UTCDateTime


# ---------------------------------------------------------------- practice


class PracticeIn(BaseModel):
    quality: int = Field(ge=0, le=5, description="0 = blank, 3 = solved with effort, 5 = instant")
    minutes: int | None = Field(None, ge=0, le=600)


class DSAProblemBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str = ""
    topic: str = Field(min_length=1, max_length=60)
    difficulty: Difficulty
    notes: str = ""


class DSAProblemUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    topic: str | None = None
    difficulty: Difficulty | None = None
    status: PracticeStatus | None = None
    notes: str | None = None


class DSAProblemRead(DSAProblemBase, ORM):
    id: int
    status: PracticeStatus
    attempts: int
    review_streak: int
    last_practiced: date | None
    next_review: date | None


class PrepQuestionBase(BaseModel):
    track: Track
    question: str = Field(min_length=1, max_length=500)
    answer: str = ""
    tags: list[str] = []


class PrepQuestionUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    tags: list[str] | None = None


class PrepQuestionRead(PrepQuestionBase, ORM):
    id: int
    source: str
    confidence: int
    review_streak: int
    last_reviewed: date | None
    next_review: date | None


class TrackSummary(BaseModel):
    track: str
    total: int
    reviewed: int
    due: int
    mastery: float  # 0-100, average confidence


# ---------------------------------------------------------------- follow-ups & progress


class FollowUpItem(BaseModel):
    kind: Literal["application", "recruiter", "dsa", "prep"]
    id: int
    title: str
    subtitle: str
    due: date
    overdue_days: int


class FollowUpComplete(BaseModel):
    reschedule_days: int | None = Field(None, ge=1, le=90)


class GoalProgress(BaseModel):
    label: str
    done: int
    goal: int


class Progress(BaseModel):
    totals: dict[str, int]
    funnel: list[dict]
    response_rate: float
    interview_rate: float
    weekly_goals: list[GoalProgress]
    applications_per_week: list[dict]
    dsa_by_difficulty: list[dict]
    dsa_by_topic: list[dict]
    prep_tracks: list[TrackSummary]
    practice_streak_days: int
    skill_gaps: list[SkillGap]

