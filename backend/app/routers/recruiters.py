from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import or_, select

from app.database.models import Recruiter, RecruiterStatus
from app.deps import DB, get_or_404
from app.schemas import RecruiterBase, RecruiterRead, RecruiterUpdate

router = APIRouter(prefix="/api/recruiters", tags=["recruiters"])

AWAITING_REPLY = {RecruiterStatus.contacted, RecruiterStatus.referral_requested}
FOLLOW_UP_AFTER_DAYS = 5


def _on_status(recruiter: Recruiter, explicit_follow_up: bool) -> None:
    if recruiter.status in AWAITING_REPLY:
        recruiter.last_contacted = recruiter.last_contacted or date.today()
        if not explicit_follow_up:
            recruiter.next_follow_up = recruiter.last_contacted + timedelta(days=FOLLOW_UP_AFTER_DAYS)
    elif recruiter.status in {RecruiterStatus.referred, RecruiterStatus.no_response} and not explicit_follow_up:
        recruiter.next_follow_up = None


@router.get("", response_model=list[RecruiterRead])
def list_recruiters(db: DB, q: str = "", status: RecruiterStatus | None = None):
    stmt = select(Recruiter)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Recruiter.name.ilike(like), Recruiter.company.ilike(like)))
    if status:
        stmt = stmt.where(Recruiter.status == status)
    return db.scalars(stmt.order_by(Recruiter.next_follow_up.asc().nulls_last(), Recruiter.id.desc())).all()


@router.post("", response_model=RecruiterRead, status_code=201)
def create_recruiter(payload: RecruiterBase, db: DB):
    recruiter = Recruiter(**payload.model_dump())
    _on_status(recruiter, explicit_follow_up=payload.next_follow_up is not None)
    db.add(recruiter)
    db.commit()
    return recruiter


@router.patch("/{recruiter_id}", response_model=RecruiterRead)
def update_recruiter(recruiter_id: int, payload: RecruiterUpdate, db: DB):
    recruiter = get_or_404(db, Recruiter, recruiter_id)
    changes = payload.model_dump(exclude_unset=True)
    status_changed = "status" in changes and changes["status"] != recruiter.status
    for key, value in changes.items():
        setattr(recruiter, key, value)
    if status_changed:
        if recruiter.status in AWAITING_REPLY and "last_contacted" not in changes:
            recruiter.last_contacted = date.today()
        _on_status(recruiter, explicit_follow_up="next_follow_up" in changes)
    db.commit()
    return recruiter


@router.delete("/{recruiter_id}", status_code=204)
def delete_recruiter(recruiter_id: int, db: DB):
    db.delete(get_or_404(db, Recruiter, recruiter_id))
    db.commit()
