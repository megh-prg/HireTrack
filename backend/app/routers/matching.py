from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Job
from app.deps import DB, get_profile
from app.jobs.matching import analyze_text, recompute_all, skill_gaps
from app.jobs.skills import extract_skills
from app.schemas import AnalyzeRequest, AnalyzeResponse, JobRead, SkillGap

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.get("", response_model=list[JobRead])
def top_matches(
    db: DB,
    min_score: float = Query(50, ge=0, le=100),
    include_tracked: bool = False,
    limit: int = Query(50, ge=1, le=500),
):
    stmt = (
        select(Job)
        .options(selectinload(Job.application))
        .where(Job.archived.is_(False), Job.match_score >= min_score)
    )
    if not include_tracked:
        stmt = stmt.where(~Job.application.has())
    return db.scalars(stmt.order_by(Job.match_score.desc()).limit(limit)).all()


@router.post("/recompute")
def recompute(db: DB) -> dict[str, int]:
    return {"rescored": recompute_all(db, get_profile(db))}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, db: DB):
    """Paste any job description and see how well it fits your profile, without saving it."""
    result = analyze_text(payload.title, payload.description, payload.location, get_profile(db))
    return AnalyzeResponse(
        score=result.score,
        skills=extract_skills(f"{payload.title}\n{payload.description}"),
        matched_skills=result.matched_skills,
        missing_skills=result.missing_skills,
        reasons=result.reasons,
    )


@router.get("/skill-gaps", response_model=list[SkillGap])
def gaps(db: DB, min_score: float = 40, limit: int = Query(10, ge=1, le=50)):
    return skill_gaps(db, min_score=min_score, limit=limit)
