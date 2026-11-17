from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database.models import Difficulty, DSAProblem, PracticeLog, PracticeStatus
from app.deps import DB, CurrentUser, get_or_404
from app.schemas import DSAProblemBase, DSAProblemRead, DSAProblemUpdate, PracticeIn
from app.services.scheduling import next_review

router = APIRouter(prefix="/api/dsa", tags=["dsa"])

DIFFICULTY_ORDER = {Difficulty.easy: 0, Difficulty.medium: 1, Difficulty.hard: 2}


@router.get("", response_model=list[DSAProblemRead])
def list_problems(
    db: DB,
    user: CurrentUser,
    topic: str | None = None,
    difficulty: Difficulty | None = None,
    status: PracticeStatus | None = None,
    due: bool = False,
):
    stmt = select(DSAProblem).where(DSAProblem.user_id == user.id)
    if topic:
        stmt = stmt.where(DSAProblem.topic == topic)
    if difficulty:
        stmt = stmt.where(DSAProblem.difficulty == difficulty)
    if status:
        stmt = stmt.where(DSAProblem.status == status)
    if due:
        stmt = stmt.where(DSAProblem.next_review <= date.today())
    problems = db.scalars(stmt).all()
    return sorted(problems, key=lambda p: (p.topic, DIFFICULTY_ORDER[p.difficulty], p.title))


@router.post("", response_model=DSAProblemRead, status_code=201)
def create_problem(payload: DSAProblemBase, db: DB, user: CurrentUser):
    if db.scalar(
        select(DSAProblem.id).where(DSAProblem.user_id == user.id, DSAProblem.title == payload.title)
    ):
        raise HTTPException(409, "Problem already exists")
    problem = DSAProblem(user_id=user.id, **payload.model_dump())
    db.add(problem)
    db.commit()
    return problem


@router.patch("/{problem_id}", response_model=DSAProblemRead)
def update_problem(problem_id: int, payload: DSAProblemUpdate, db: DB, user: CurrentUser):
    problem = get_or_404(db, DSAProblem, problem_id, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(problem, key, value)
    db.commit()
    return problem


@router.post("/{problem_id}/practice", response_model=DSAProblemRead)
def log_practice(problem_id: int, payload: PracticeIn, db: DB, user: CurrentUser):
    problem = get_or_404(db, DSAProblem, problem_id, user)
    today = date.today()
    problem.attempts += 1
    problem.last_practiced = today
    problem.review_streak, problem.next_review = next_review(payload.quality, problem.review_streak, today)
    if payload.quality < 3:
        problem.status = PracticeStatus.attempted
    elif problem.review_streak >= 3 and payload.quality >= 4:
        problem.status = PracticeStatus.mastered
    else:
        problem.status = PracticeStatus.solved
    db.add(
        PracticeLog(
            user_id=user.id, kind="dsa", item_id=problem.id, quality=payload.quality, minutes=payload.minutes
        )
    )
    db.commit()
    return problem


@router.delete("/{problem_id}", status_code=204)
def delete_problem(problem_id: int, db: DB, user: CurrentUser):
    db.delete(get_or_404(db, DSAProblem, problem_id, user))
    db.commit()
