from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Application, Job, Stage, StageEvent
from app.deps import DB, get_or_404
from app.jobs.ingestion import upsert_jobs
from app.schemas import ApplicationCreate, ApplicationRead, ApplicationUpdate

router = APIRouter(prefix="/api/applications", tags=["applications"])

FOLLOW_UP_AFTER_DAYS = {
    Stage.applied: 7,
    Stage.recruiter_screen: 3,
    Stage.assessment: 3,
    Stage.technical: 4,
    Stage.final: 4,
}
CLOSED = {Stage.offer, Stage.rejected, Stage.withdrawn}


def _apply_stage(application: Application, stage: Stage, previous: Stage | None) -> None:
    """Record the transition and set sensible dates so nothing silently goes stale."""
    application.events.append(StageEvent(from_stage=previous, to_stage=stage))
    application.stage = stage
    today = date.today()
    if stage != Stage.saved and application.applied_on is None:
        application.applied_on = today
    if stage in CLOSED:
        application.next_follow_up = None
    elif stage in FOLLOW_UP_AFTER_DAYS:
        application.next_follow_up = today + timedelta(days=FOLLOW_UP_AFTER_DAYS[stage])


def _load(db, application_id: int) -> Application:
    stmt = (
        select(Application)
        .options(selectinload(Application.job), selectinload(Application.events))
        .where(Application.id == application_id)
    )
    application = db.scalar(stmt)
    if application is None:
        raise HTTPException(404, f"Application {application_id} not found")
    return application


@router.get("", response_model=list[ApplicationRead])
def list_applications(db: DB, stage: Stage | None = None):
    stmt = select(Application).options(
        selectinload(Application.job), selectinload(Application.events)
    )
    if stage:
        stmt = stmt.where(Application.stage == stage)
    return db.scalars(stmt.order_by(Application.updated_at.desc())).all()


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(payload: ApplicationCreate, db: DB):
    if payload.job is not None:
        result = upsert_jobs(db, [payload.job], source="manual")
        if not result.created:
            raise HTTPException(409, "This job already exists — track it from the Jobs page")
        job_id = result.created_ids[0]
    else:
        job_id = get_or_404(db, Job, payload.job_id).id

    if db.scalar(select(Application.id).where(Application.job_id == job_id)):
        raise HTTPException(409, "You are already tracking this job")

    application = Application(
        job_id=job_id,
        stage=payload.stage,
        applied_on=payload.applied_on,
        referral=payload.referral,
        notes=payload.notes,
    )
    _apply_stage(application, payload.stage, previous=None)
    if payload.next_follow_up:
        application.next_follow_up = payload.next_follow_up
    db.add(application)
    db.commit()
    return _load(db, application.id)


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(application_id: int, payload: ApplicationUpdate, db: DB):
    application = _load(db, application_id)
    changes = payload.model_dump(exclude_unset=True)
    stage = changes.pop("stage", None)
    if stage is not None and stage != application.stage:
        _apply_stage(application, stage, previous=application.stage)
    for key, value in changes.items():
        setattr(application, key, value)
    db.commit()
    return _load(db, application_id)


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: int, db: DB):
    db.delete(get_or_404(db, Application, application_id))
    db.commit()
