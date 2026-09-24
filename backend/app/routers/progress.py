from collections import Counter, defaultdict
from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.database.models import (
    Application,
    DSAProblem,
    Job,
    PracticeLog,
    PracticeStatus,
    PrepQuestion,
    Recruiter,
    RecruiterStatus,
    Stage,
)
from app.deps import DB, get_profile
from app.jobs.matching import skill_gaps
from app.routers.prep import track_summaries
from app.schemas import GoalProgress, Progress

router = APIRouter(prefix="/api/progress", tags=["progress"])

FUNNEL = [
    Stage.applied,
    Stage.recruiter_screen,
    Stage.assessment,
    Stage.technical,
    Stage.final,
    Stage.offer,
]
FUNNEL_INDEX = {s: i for i, s in enumerate(FUNNEL)}
SOLVED = {PracticeStatus.solved, PracticeStatus.mastered}


def _furthest_stage(application: Application) -> int:
    """Index into FUNNEL of the furthest stage ever reached (-1 = never applied)."""
    reached = [FUNNEL_INDEX[e.to_stage] for e in application.events if e.to_stage in FUNNEL_INDEX]
    return max(reached, default=-1)


def _streak(active_days: set[date], today: date) -> int:
    day = today if today in active_days else today - timedelta(days=1)
    streak = 0
    while day in active_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


@router.get("", response_model=Progress)
def progress(db: DB):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    profile = get_profile(db)

    applications = db.scalars(select(Application).options(selectinload(Application.events))).all()
    furthest = [_furthest_stage(a) for a in applications]
    applied = sum(1 for f in furthest if f >= 0)
    responded = sum(1 for f in furthest if f >= FUNNEL_INDEX[Stage.recruiter_screen])
    interviewed = sum(1 for f in furthest if f >= FUNNEL_INDEX[Stage.technical])

    recruiters = db.scalars(select(Recruiter)).all()
    problems = db.scalars(select(DSAProblem)).all()
    logs = db.scalars(select(PracticeLog).where(PracticeLog.at >= today - timedelta(days=120))).all()

    # Weekly applications for the last 8 weeks, oldest first.
    weekly = Counter(
        a.applied_on - timedelta(days=a.applied_on.weekday()) for a in applications if a.applied_on
    )
    applications_per_week = [
        {"week": (week_start - timedelta(weeks=i)).isoformat(), "count": weekly.get(week_start - timedelta(weeks=i), 0)}
        for i in range(7, -1, -1)
    ]

    by_difficulty: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_topic: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for p in problems:
        for bucket in (by_difficulty[p.difficulty.value], by_topic[p.topic]):
            bucket[0] += 1
            bucket[1] += p.status in SOLVED

    active_days = {log.at.date() for log in logs} | {a.applied_on for a in applications if a.applied_on}

    return Progress(
        totals={
            "jobs": db.scalar(select(func.count()).select_from(Job).where(Job.archived.is_(False))) or 0,
            "applications": applied,
            "active": sum(1 for a in applications if a.stage not in {Stage.saved, Stage.offer, Stage.rejected, Stage.withdrawn}),
            "interviews": interviewed,
            "offers": sum(1 for a in applications if a.stage == Stage.offer),
            "recruiters": len(recruiters),
            "recruiters_replied": sum(
                1 for r in recruiters if r.status in {RecruiterStatus.replied, RecruiterStatus.referred}
            ),
            "referrals": sum(1 for r in recruiters if r.status == RecruiterStatus.referred),
            "dsa_solved": sum(1 for p in problems if p.status in SOLVED),
            "dsa_total": len(problems),
            "prep_reviewed": db.scalar(select(func.count()).select_from(PrepQuestion).where(PrepQuestion.last_reviewed.is_not(None))) or 0,
            "prep_total": db.scalar(select(func.count()).select_from(PrepQuestion)) or 0,
        },
        funnel=[{"stage": s.value, "count": sum(1 for f in furthest if f >= i)} for i, s in enumerate(FUNNEL)],
        response_rate=round(responded / applied * 100, 1) if applied else 0.0,
        interview_rate=round(interviewed / applied * 100, 1) if applied else 0.0,
        weekly_goals=[
            GoalProgress(
                label="Applications",
                done=sum(1 for a in applications if a.applied_on and a.applied_on >= week_start),
                goal=profile.weekly_application_goal,
            ),
            GoalProgress(
                label="DSA problems",
                done=sum(1 for log in logs if log.kind == "dsa" and log.at.date() >= week_start),
                goal=profile.weekly_dsa_goal,
            ),
            GoalProgress(
                label="Recruiter outreach",
                done=sum(1 for r in recruiters if r.last_contacted and r.last_contacted >= week_start),
                goal=profile.weekly_outreach_goal,
            ),
        ],
        applications_per_week=applications_per_week,
        dsa_by_difficulty=[
            {"difficulty": d, "total": by_difficulty[d][0], "solved": by_difficulty[d][1]}
            for d in ("easy", "medium", "hard")
        ],
        dsa_by_topic=[
            {"topic": t, "total": v[0], "solved": v[1]} for t, v in sorted(by_topic.items())
        ],
        prep_tracks=track_summaries(db),
        practice_streak_days=_streak(active_days, today),
        skill_gaps=skill_gaps(db, limit=8),
    )
