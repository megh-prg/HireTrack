"""Orchestrates the resume-optimization flow for one resume against one job.

Degrades gracefully in three tiers:
  * The before-score is always computed (deterministic, no AI).
  * JD keywords come from Gemini; if that's unavailable we fall back to the
    job's already-extracted skills so the score still means something.
  * The AI rewrite + after-score only run when Gemini is configured.
"""

from typing import Any

from app.optimizer.ai import (
    AIServiceUnavailable,
    ai_available,
    generate_optimized_resume,
    stringify_resume_item,
)
from app.optimizer.ats import score_resume_against_jd
from app.optimizer.grounding import ground_optimized_resume
from app.optimizer.jd import analyze_job_description


def resume_dict_to_text(resume: dict[str, Any]) -> str:
    """Flatten an optimized-resume dict back into text so it can be re-scored."""
    parts: list[str] = []
    if summary := resume.get("summary"):
        parts.append(stringify_resume_item(summary))
    if skills := resume.get("skills"):
        parts.append("Skills: " + ", ".join(stringify_resume_item(s) for s in skills))
    for section in ("experience", "projects", "education", "certifications"):
        for item in resume.get(section) or []:
            parts.append("- " + stringify_resume_item(item))
    return "\n".join(parts)


def optimize_resume_for_job(
    resume_text: str,
    job_description: str,
    fallback_keywords: list[str] | None = None,
) -> dict[str, Any]:
    jd = analyze_job_description(job_description)
    keywords = jd["keywords"] or [k.lower() for k in (fallback_keywords or [])]
    required = jd["required_skills"]
    preferred = jd["preferred_skills"]

    before = score_resume_against_jd(resume_text, keywords, required, preferred)

    result: dict[str, Any] = {
        "ai_available": ai_available(),
        "keywords": keywords,
        "required_skills": required,
        "preferred_skills": preferred,
        "score_before": before["score"],
        "missing_keywords": before["missing_keywords"],
        "weak_sections": before["weak_sections"],
        "breakdown_before": before["breakdown"],
        "score_after": None,
        "optimized_resume": None,
        "unsupported_claims": [],
        "is_grounded": None,
    }

    if not ai_available():
        return result

    try:
        raw = generate_optimized_resume(resume_text, job_description)
    except AIServiceUnavailable:
        result["ai_available"] = False
        return result

    grounded = ground_optimized_resume(resume_text, raw, keywords)
    optimized_resume = grounded["resume"]
    after = score_resume_against_jd(resume_dict_to_text(optimized_resume), keywords, required, preferred)

    result.update(
        score_after=after["score"],
        optimized_resume=optimized_resume,
        unsupported_claims=grounded["unsupported_claims"],
        is_grounded=grounded["is_grounded"],
        breakdown_after=after["breakdown"],
    )
    return result
