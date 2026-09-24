"""Load interview-prep content from /prep and optional demo data. Safe to run repeatedly."""

import csv
import re
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    Application,
    Difficulty,
    DSAProblem,
    Job,
    PrepQuestion,
    Profile,
    Recruiter,
    RecruiterStatus,
    Stage,
    StageEvent,
)
from app.jobs.ingestion import upsert_jobs
from app.schemas import PREP_TRACKS, JobCreate

QUESTION_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)
TAGS_LINE = re.compile(r"^tags:\s*(.+)$", re.I | re.M)


def parse_questions(markdown: str) -> list[dict]:
    """`## Question` headings; everything until the next heading is the model answer."""
    matches = list(QUESTION_HEADING.finditer(markdown))
    questions = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[match.end():end].strip()
        tags: list[str] = []
        if tag_match := TAGS_LINE.search(body):
            tags = [t.strip() for t in tag_match.group(1).split(",") if t.strip()]
            body = TAGS_LINE.sub("", body).strip()
        questions.append({"question": match.group(1), "answer": body, "tags": tags})
    return questions


def seed_prep(db: Session, prep_dir: Path) -> int:
    existing = set(db.execute(select(PrepQuestion.track, PrepQuestion.question)).tuples())
    added = 0
    for track in PREP_TRACKS:
        path = prep_dir / track / "questions.md"
        if not path.exists():
            continue
        for q in parse_questions(path.read_text(encoding="utf-8")):
            if (track, q["question"]) in existing:
                continue
            db.add(PrepQuestion(track=track, **q))
            added += 1
    db.commit()
    return added


def seed_dsa(db: Session, prep_dir: Path) -> int:
    path = prep_dir / "dsa" / "problems.csv"
    if not path.exists():
        return 0
    existing = set(db.scalars(select(DSAProblem.title)))
    added = 0
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["title"] in existing:
                continue
            db.add(
                DSAProblem(
                    title=row["title"],
                    topic=row["topic"],
                    difficulty=Difficulty(row["difficulty"].lower()),
                    url=row.get("url", ""),
                )
            )
            added += 1
    db.commit()
    return added


def seed_profile(db: Session) -> Profile:
    profile = db.get(Profile, 1)
    if profile is None:
        profile = Profile(
            id=1,
            name="",
            target_roles=["AI Engineer", "GenAI Engineer", "AI Backend Engineer", "Python Backend Engineer"],
            locations=["Bengaluru", "Remote India"],
            open_to_remote=True,
            skills=["Python", "FastAPI", "SQL", "PostgreSQL", "Docker", "REST API", "LLM", "RAG", "LangChain", "Git"],
            experience_years=2,
            salary_expectation="₹7–12+ LPA",
        )
        db.add(profile)
        db.commit()
    return profile


DEMO_JOBS = [
    JobCreate(
        title="AI Engineer",
        company="Northwind Labs (demo)",
        location="Bengaluru",
        salary="₹10–14 LPA",
        description="Build RAG pipelines with LangChain and a vector database (pgvector). "
        "Python, FastAPI, PostgreSQL, Docker. Experience with LLM evaluation and prompt engineering.",
    ),
    JobCreate(
        title="Python Backend Engineer",
        company="Contoso Fintech (demo)",
        location="Remote India",
        remote=True,
        salary="₹8–12 LPA",
        description="Design REST APIs in FastAPI, SQLAlchemy and PostgreSQL. Redis, Celery, Kafka, "
        "Docker and Kubernetes on AWS. Strong system design and pytest discipline.",
    ),
    JobCreate(
        title="GenAI Engineer",
        company="Fabrikam Health (demo)",
        location="Hyderabad",
        salary="₹12–18 LPA",
        description="Fine-tuning with LoRA, Hugging Face transformers, PyTorch. Build AI agents with "
        "tool calling, embeddings, and evals. Python and GCP Vertex AI.",
    ),
    JobCreate(
        title="Senior Backend Engineer (Go)",
        company="Tailspin Logistics (demo)",
        location="Pune",
        description="Golang microservices, gRPC, Kafka, Kubernetes, Terraform on AWS. 6+ years.",
    ),
    JobCreate(
        title="AI Backend Engineer",
        company="Adventure Works AI (demo)",
        location="Bengaluru",
        salary="₹9–13 LPA",
        description="Python, FastAPI, async programming, PostgreSQL, Redis and Docker. Integrate LLM "
        "APIs, build RAG with embeddings, ship CI/CD with GitHub Actions.",
    ),
]


def seed_demo(db: Session) -> None:
    if db.scalar(select(Job.id).limit(1)):
        return
    result = upsert_jobs(db, DEMO_JOBS, source="demo")
    today = date.today()
    plan = [
        (result.created_ids[0], [Stage.applied, Stage.recruiter_screen], 9, today + timedelta(days=1)),
        (result.created_ids[1], [Stage.applied], 8, today - timedelta(days=1)),
        (result.created_ids[4], [Stage.saved], 0, None),
    ]
    for job_id, stages, days_ago, follow_up in plan:
        applied_on = today - timedelta(days=days_ago) if stages[0] != Stage.saved else None
        app = Application(job_id=job_id, stage=stages[-1], applied_on=applied_on, next_follow_up=follow_up)
        previous = None
        for stage in stages:
            app.events.append(StageEvent(from_stage=previous, to_stage=stage))
            previous = stage
        db.add(app)
    db.add_all(
        [
            Recruiter(
                name="Priya (demo)",
                company="Northwind Labs (demo)",
                title="Talent Partner",
                status=RecruiterStatus.replied,
                last_contacted=today - timedelta(days=3),
                next_follow_up=today + timedelta(days=2),
                notes="Asked for availability next week.",
            ),
            Recruiter(
                name="Arjun (demo)",
                company="Contoso Fintech (demo)",
                title="Engineering Manager",
                status=RecruiterStatus.referral_requested,
                last_contacted=today - timedelta(days=6),
                next_follow_up=today - timedelta(days=1),
            ),
        ]
    )
    db.commit()


def run_seed(db: Session, prep_dir: Path, demo: bool) -> None:
    seed_profile(db)
    seed_prep(db, prep_dir)
    seed_dsa(db, prep_dir)
    if demo:
        seed_demo(db)
