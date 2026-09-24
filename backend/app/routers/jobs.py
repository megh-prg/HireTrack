from typing import Literal

from fastapi import APIRouter, HTTPException, Query, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.database.models import Job
from app.deps import DB, get_or_404, get_profile
from app.jobs.ingestion import parse_upload, upsert_jobs
from app.jobs.matching import apply_match
from app.jobs.skills import extract_skills
from app.schemas import IngestResponse, JobCreate, JobRead, JobUpdate

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

MAX_UPLOAD_BYTES = 2 * 1024 * 1024


@router.get("", response_model=list[JobRead])
def list_jobs(
    db: DB,
    q: str = "",
    source: str | None = None,
    min_score: float | None = None,
    include_archived: bool = False,
    untracked: bool = False,
    sort: Literal["newest", "score"] = "newest",
    limit: int = Query(200, ge=1, le=1000),
):
    stmt = select(Job).options(selectinload(Job.application))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Job.title.ilike(like), Job.company.ilike(like), Job.location.ilike(like)))
    if source:
        stmt = stmt.where(Job.source == source)
    if min_score is not None:
        stmt = stmt.where(Job.match_score >= min_score)
    if not include_archived:
        stmt = stmt.where(Job.archived.is_(False))
    if untracked:
        stmt = stmt.where(~Job.application.has())
    order = Job.match_score.desc().nulls_last() if sort == "score" else Job.created_at.desc()
    return db.scalars(stmt.order_by(order, Job.id.desc()).limit(limit)).all()


@router.post("", response_model=JobRead, status_code=201)
def create_job(payload: JobCreate, db: DB):
    result = upsert_jobs(db, [payload], source="manual")
    if not result.created:
        raise HTTPException(409, "This job is already in your list")
    return db.get(Job, result.created_ids[0])


@router.get("/{job_id}", response_model=JobRead)
def read_job(job_id: int, db: DB):
    return get_or_404(db, Job, job_id)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: int, payload: JobUpdate, db: DB):
    job = get_or_404(db, Job, job_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(job, key, value)
    if {"title", "description"} & changes.keys():
        job.skills = extract_skills(f"{job.title}\n{job.description}")
    apply_match(job, get_profile(db))
    db.commit()
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: DB):
    db.delete(get_or_404(db, Job, job_id))
    db.commit()


@router.post("/import", response_model=IngestResponse)
def import_jobs(payload: list[JobCreate], db: DB):
    return upsert_jobs(db, payload, source="import")


@router.post("/upload", response_model=IngestResponse)
async def upload_jobs(file: UploadFile, db: DB):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 2 MB)")
    try:
        jobs = parse_upload(file.filename or "upload.csv", content)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(422, f"Could not parse file: {exc}") from exc
    return upsert_jobs(db, jobs, source="upload")
