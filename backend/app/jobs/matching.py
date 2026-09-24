"""Explainable job-to-profile matching.

score = 55% skill coverage + 30% title fit + 15% location fit, scaled to 0-100.
Every score comes with the matched and missing skills so the UI can say *why*.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Job, Profile
from app.jobs.skills import SKILL_TO_TRACK, canonicalize, extract_skills

SKILL_WEIGHT, TITLE_WEIGHT, LOCATION_WEIGHT = 0.55, 0.30, 0.15
SENIOR_TITLE = re.compile(r"\b(senior|sr\.?|staff|principal|lead|head|director|architect)\b", re.I)
STOPWORDS = {"and", "or", "the", "of", "a", "an", "i", "ii", "iii", "-", "/", "&", "remote"}


@dataclass
class MatchResult:
    score: float
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#.]+", text.lower()) if t not in STOPWORDS}


def title_fit(title: str, target_roles: list[str]) -> float:
    if not target_roles:
        return 0.5
    title_l = title.lower()
    title_tokens = _tokens(title)
    best = 0.0
    for role in target_roles:
        if role.lower() in title_l:
            return 1.0
        role_tokens = _tokens(role)
        if role_tokens:
            best = max(best, len(role_tokens & title_tokens) / len(role_tokens))
    return best


GLOBAL_REMOTE = re.compile(r"\b(worldwide|anywhere|global|remote)\b", re.I)
NO_SKILLS_SCORE = 0.2  # a posting we can't read skills from shouldn't look like a decent match


def _place_tokens(locations: list[str]) -> set[str]:
    return {t for loc in locations for t in _tokens(loc) if len(t) > 2}


def location_fit(location: str, remote: bool, profile: Profile) -> float:
    """1 = fits, 0.4 = remote but restricted to regions you didn't list, 0.3 = unknown, 0 = mismatch."""
    location_l = location.lower().strip()
    places = _place_tokens(profile.locations)
    names_your_place = bool(places & _tokens(location_l))
    if remote and profile.open_to_remote:
        # Remote postings often restrict where candidates may live ("USA only", "Europe").
        leftover = GLOBAL_REMOTE.sub("", location_l).strip(" ,/-·")
        return 1.0 if not leftover or names_your_place else 0.4
    if not location_l:
        return 0.3
    return 1.0 if names_your_place else 0.0


def score_job(
    *,
    title: str,
    job_skills: list[str],
    location: str,
    remote: bool,
    profile: Profile,
) -> MatchResult:
    profile_skills = set(canonicalize(profile.skills))
    matched = [s for s in job_skills if s in profile_skills]
    missing = [s for s in job_skills if s not in profile_skills]
    skill = len(matched) / len(job_skills) if job_skills else NO_SKILLS_SCORE
    title_score = title_fit(title, profile.target_roles)
    loc = location_fit(location, remote, profile)

    raw = SKILL_WEIGHT * skill + TITLE_WEIGHT * title_score + LOCATION_WEIGHT * loc
    reasons = [
        f"{len(matched)}/{len(job_skills)} required skills" if job_skills else "No skills listed",
        f"title fit {round(title_score * 100)}%",
        {1.0: "location fits", 0.4: "remote, but region-restricted", 0.3: "location unknown"}.get(loc, "location mismatch"),
    ]
    if SENIOR_TITLE.search(title) and profile.experience_years < 4:
        raw *= 0.75
        reasons.append("senior title vs. your experience")
    return MatchResult(round(raw * 100, 1), matched, missing, reasons)


def apply_match(job: Job, profile: Profile) -> MatchResult:
    result = score_job(
        title=job.title,
        job_skills=job.skills,
        location=job.location,
        remote=job.remote,
        profile=profile,
    )
    job.match_score = result.score
    job.matched_skills = result.matched_skills
    job.missing_skills = result.missing_skills
    return result


def analyze_text(title: str, description: str, location: str, profile: Profile) -> MatchResult:
    """Score a pasted job description without saving it."""
    skills = extract_skills(f"{title}\n{description}")
    remote = "remote" in f"{location} {title}".lower()
    return score_job(title=title, job_skills=skills, location=location, remote=remote, profile=profile)


def recompute_all(db: Session, profile: Profile) -> int:
    jobs = db.scalars(select(Job).where(Job.archived.is_(False))).all()
    for job in jobs:
        apply_match(job, profile)
    db.commit()
    return len(jobs)


def skill_gaps(db: Session, min_score: float = 40, limit: int = 10) -> list[dict]:
    """Skills most often missing from jobs you are a reasonable fit for."""
    jobs = db.scalars(
        select(Job).where(Job.archived.is_(False), Job.match_score >= min_score)
    ).all()
    counts = Counter(skill for job in jobs for skill in job.missing_skills)
    return [
        {"skill": skill, "jobs": count, "track": SKILL_TO_TRACK.get(skill)}
        for skill, count in counts.most_common(limit)
    ]
