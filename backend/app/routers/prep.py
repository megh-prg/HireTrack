from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import case, func, or_, select

from app.database.models import PracticeLog, PrepQuestion
from app.deps import DB, get_or_404
from app.jobs.matching import skill_gaps
from app.schemas import (
    PREP_TRACKS,
    PracticeIn,
    PrepQuestionBase,
    PrepQuestionRead,
    PrepQuestionUpdate,
    Track,
    TrackSummary,
)
from app.services.scheduling import next_review

router = APIRouter(prefix="/api/prep", tags=["interview prep"])


def track_summaries(db) -> list[TrackSummary]:
    today = date.today()
    rows = db.execute(
        select(
            PrepQuestion.track,
            func.count(),
            func.count(PrepQuestion.last_reviewed),
            func.sum(case((PrepQuestion.next_review <= today, 1), else_=0)),
            func.avg(PrepQuestion.confidence),
        ).group_by(PrepQuestion.track)
    ).all()
    by_track = {r[0]: r for r in rows}
    return [
        TrackSummary(
            track=t,
            total=by_track[t][1] if t in by_track else 0,
            reviewed=by_track[t][2] if t in by_track else 0,
            due=int(by_track[t][3] or 0) if t in by_track else 0,
            mastery=round(float(by_track[t][4] or 0) / 5 * 100, 1) if t in by_track else 0.0,
        )
        for t in PREP_TRACKS
    ]


@router.get("/tracks", response_model=list[TrackSummary])
def tracks(db: DB):
    return track_summaries(db)


@router.get("/questions", response_model=list[PrepQuestionRead])
def list_questions(db: DB, track: Track | None = None, due: bool = False, q: str = ""):
    stmt = select(PrepQuestion)
    if track:
        stmt = stmt.where(PrepQuestion.track == track)
    if due:
        stmt = stmt.where(
            or_(PrepQuestion.next_review.is_(None), PrepQuestion.next_review <= date.today())
        )
    if q:
        stmt = stmt.where(PrepQuestion.question.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(PrepQuestion.track, PrepQuestion.id)).all()


@router.get("/recommended", response_model=list[PrepQuestionRead])
def recommended(db: DB, limit: int = Query(10, ge=1, le=50)):
    """Personalised queue: weakest questions from the tracks your target jobs need most."""
    gap_tracks = [g["track"] for g in skill_gaps(db, limit=20) if g["track"] and g["track"] != "dsa"]
    ordered_tracks = list(dict.fromkeys(gap_tracks + list(PREP_TRACKS)))
    rank = {t: i for i, t in enumerate(ordered_tracks)}
    today = date.today()
    candidates = db.scalars(
        select(PrepQuestion).where(
            or_(PrepQuestion.next_review.is_(None), PrepQuestion.next_review <= today)
        )
    ).all()
    candidates.sort(key=lambda p: (rank.get(p.track, 99), p.confidence, p.id))
    return candidates[:limit]


@router.post("/questions", response_model=PrepQuestionRead, status_code=201)
def create_question(payload: PrepQuestionBase, db: DB):
    exists = db.scalar(
        select(PrepQuestion.id).where(
            PrepQuestion.track == payload.track, PrepQuestion.question == payload.question
        )
    )
    if exists:
        raise HTTPException(409, "Question already exists in this track")
    question = PrepQuestion(**payload.model_dump(), source="user")
    db.add(question)
    db.commit()
    return question


@router.patch("/questions/{question_id}", response_model=PrepQuestionRead)
def update_question(question_id: int, payload: PrepQuestionUpdate, db: DB):
    question = get_or_404(db, PrepQuestion, question_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, key, value)
    db.commit()
    return question


@router.post("/questions/{question_id}/review", response_model=PrepQuestionRead)
def review_question(question_id: int, payload: PracticeIn, db: DB):
    question = get_or_404(db, PrepQuestion, question_id)
    today = date.today()
    question.confidence = payload.quality
    question.last_reviewed = today
    question.review_streak, question.next_review = next_review(
        payload.quality, question.review_streak, today
    )
    db.add(PracticeLog(kind="prep", item_id=question.id, quality=payload.quality, minutes=payload.minutes))
    db.commit()
    return question


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: int, db: DB):
    db.delete(get_or_404(db, PrepQuestion, question_id))
    db.commit()
