from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Application, DSAProblem, PrepQuestion, Recruiter
from app.deps import DB, get_or_404
from app.routers.applications import CLOSED
from app.schemas import FollowUpComplete, FollowUpItem

router = APIRouter(prefix="/api/followups", tags=["follow-ups"])

STAGE_LABEL = {
    "applied": "Applied — nudge the recruiter",
    "recruiter_screen": "Recruiter screen — send thank-you / confirm next step",
    "assessment": "Assessment — check status",
    "technical": "Technical round — follow up on feedback",
    "final": "Final round — follow up on decision",
    "saved": "Saved — apply or archive",
}


@router.get("", response_model=list[FollowUpItem])
def upcoming(db: DB, horizon_days: int = Query(7, ge=0, le=60)):
    today = date.today()
    until = today + timedelta(days=horizon_days)
    items: list[FollowUpItem] = []

    def add(kind, item_id, title, subtitle, due):
        items.append(
            FollowUpItem(
                kind=kind,
                id=item_id,
                title=title,
                subtitle=subtitle,
                due=due,
                overdue_days=max(0, (today - due).days),
            )
        )

    applications = db.scalars(
        select(Application)
        .options(selectinload(Application.job))
        .where(Application.next_follow_up <= until, Application.stage.not_in(CLOSED))
    ).all()
    for a in applications:
        add("application", a.id, f"{a.job.title} · {a.job.company}", STAGE_LABEL.get(a.stage.value, a.stage.value), a.next_follow_up)

    for r in db.scalars(select(Recruiter).where(Recruiter.next_follow_up <= until)).all():
        label = " at ".join(part for part in (r.title, r.company) if part) or "Recruiter"
        add("recruiter", r.id, r.name, f"{label} — {r.status.value.replace('_', ' ')}", r.next_follow_up)

    for p in db.scalars(select(DSAProblem).where(DSAProblem.next_review <= today)).all():
        add("dsa", p.id, p.title, f"DSA review · {p.topic} · {p.difficulty.value}", p.next_review)

    for q in db.scalars(select(PrepQuestion).where(PrepQuestion.next_review <= today)).all():
        add("prep", q.id, q.question, f"{q.track} review", q.next_review)

    return sorted(items, key=lambda i: (i.due, i.kind))


@router.post("/{kind}/{item_id}/complete", status_code=204)
def complete(
    kind: Literal["application", "recruiter"],
    item_id: int,
    db: DB,
    payload: FollowUpComplete | None = None,
):
    """Mark a follow-up done. Optionally schedule the next one `reschedule_days` from today."""
    today = date.today()
    days = payload.reschedule_days if payload else None
    next_date = today + timedelta(days=days) if days else None
    if kind == "application":
        application = get_or_404(db, Application, item_id)
        application.next_follow_up = next_date
    elif kind == "recruiter":
        recruiter = get_or_404(db, Recruiter, item_id)
        recruiter.last_contacted = today
        recruiter.next_follow_up = next_date
    else:  # pragma: no cover - guarded by Literal
        raise HTTPException(400, "Unsupported follow-up kind")
    db.commit()
