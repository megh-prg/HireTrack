from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import JobSource
from app.deps import DB, get_or_404
from app.jobs.ingestion import upsert_jobs
from app.jobs.sources import SourceError, SourceQuery, apply_filters, fetch, parse_careers_url
from app.schemas import JobSourceCreate, JobSourceRead, JobSourceUpdate, SourceRunResult

router = APIRouter(prefix="/api/sources", tags=["job sources"])


def run_source(db: Session, source: JobSource) -> SourceRunResult:
    """Fetch, filter and store one source. Errors are recorded on the source, not raised."""
    found = created = duplicates = 0
    try:
        jobs = fetch(
            SourceQuery(
                kind=source.kind,
                query=source.query,
                location=source.location,
                company_name=source.company_name,
                limit=source.limit,
            )
        )
        jobs = apply_filters(jobs, source.title_keywords, source.location_keywords)[: source.limit]
        result = upsert_jobs(db, jobs, source=source.kind)
        found, created, duplicates = len(jobs), result.created, result.duplicates
        source.last_error = ""
    except SourceError as exc:
        source.last_error = str(exc)
    source.last_run_at = datetime.now(timezone.utc)
    source.last_found, source.last_created = found, created
    db.commit()
    return SourceRunResult(
        source=JobSourceRead.model_validate(source), found=found, created=created, duplicates=duplicates
    )


def refresh_stale(db: Session, older_than_hours: float) -> int:
    """Run every enabled source not refreshed within the window. Used by the background loop."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    ran = 0
    for source in db.scalars(select(JobSource).where(JobSource.enabled.is_(True))).all():
        last = source.last_run_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last is None or last < cutoff:
            run_source(db, source)
            ran += 1
    return ran


@router.get("", response_model=list[JobSourceRead])
def list_sources(db: DB):
    return db.scalars(select(JobSource).order_by(JobSource.kind, JobSource.query)).all()


@router.post("", response_model=SourceRunResult, status_code=201)
def create_source(payload: JobSourceCreate, db: DB):
    kind, query = payload.kind, payload.query.strip()
    if payload.url:
        parsed = parse_careers_url(payload.url)
        if not parsed:
            raise HTTPException(
                422,
                "Unrecognised careers URL. Supported: boards.greenhouse.io/<company>, "
                "jobs.lever.co/<company>, jobs.ashbyhq.com/<company>",
            )
        kind, query = parsed
    if not kind or not query:
        raise HTTPException(422, "Provide a careers URL, or a source type with a company slug / search")

    exists = db.scalar(
        select(JobSource.id).where(
            JobSource.kind == kind, JobSource.query == query, JobSource.location == payload.location
        )
    )
    if exists:
        raise HTTPException(409, "This source is already saved — use Refresh")

    source = JobSource(
        kind=kind,
        query=query,
        location=payload.location,
        company_name=payload.company_name,
        title_keywords=payload.title_keywords,
        location_keywords=payload.location_keywords,
        limit=payload.limit,
    )
    db.add(source)
    db.flush()
    result = run_source(db, source)
    if source.last_error:
        # Don't keep a source that can't be fetched (typo in the slug, missing API key…).
        message = source.last_error
        db.delete(source)
        db.commit()
        raise HTTPException(422, message)
    return result


@router.patch("/{source_id}", response_model=JobSourceRead)
def update_source(source_id: int, payload: JobSourceUpdate, db: DB):
    source = get_or_404(db, JobSource, source_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    db.commit()
    return source


@router.post("/{source_id}/run", response_model=SourceRunResult)
def run_one(source_id: int, db: DB):
    return run_source(db, get_or_404(db, JobSource, source_id))


@router.post("/run-all", response_model=list[SourceRunResult])
def run_all(db: DB):
    sources = db.scalars(select(JobSource).where(JobSource.enabled.is_(True))).all()
    return [run_source(db, s) for s in sources]


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: DB):
    """Stops future imports; jobs already imported stay in your list."""
    db.delete(get_or_404(db, JobSource, source_id))
    db.commit()
