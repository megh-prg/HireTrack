"""Anti-hallucination layer: check AI-generated resume content against the
original resume before it reaches the user.

Both checks are deterministic (no extra LLM call): skills the AI added that
don't appear in the source resume are stripped, and JD keywords that only
show up after rewriting are flagged.
"""

import re
from typing import Any, Optional

from app.optimizer.ai import stringify_resume_item


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", " ", text.lower())


def _contains(normalized_text: str, phrase: str) -> bool:
    """Word-boundary check -- plain ``in`` would let "java" match inside
    "javascript" and falsely mark a fabricated skill as supported."""
    return re.search(rf"\b{re.escape(phrase)}\b", normalized_text) is not None


def _is_supported(claim: str, normalized_source: str) -> bool:
    normalized_claim = _normalize(claim).strip()
    if not normalized_claim:
        return True
    return _contains(normalized_source, normalized_claim)


def ground_optimized_resume(
    original_text: str,
    optimized_resume: dict[str, Any],
    jd_keywords: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Strip unsupported skills and flag padded keywords in the AI rewrite."""
    normalized_source = _normalize(original_text)

    skills = optimized_resume.get("skills") or []
    kept_skills: list[Any] = []
    unsupported_skills: list[str] = []
    for skill in skills:
        skill_text = stringify_resume_item(skill)
        if _is_supported(skill_text, normalized_source):
            kept_skills.append(skill)
        else:
            unsupported_skills.append(skill_text)

    unsupported_keyword_mentions: list[str] = []
    if jd_keywords:
        narrative = " ".join(
            stringify_resume_item(item)
            for item in (
                [optimized_resume.get("summary", "")]
                + list(optimized_resume.get("experience") or [])
                + list(optimized_resume.get("projects") or [])
            )
        )
        normalized_narrative = _normalize(narrative)
        for keyword in jd_keywords:
            normalized_keyword = _normalize(keyword).strip()
            if not normalized_keyword:
                continue
            if _contains(normalized_narrative, normalized_keyword) and not _contains(
                normalized_source, normalized_keyword
            ):
                unsupported_keyword_mentions.append(keyword)

    grounded_resume = dict(optimized_resume)
    grounded_resume["skills"] = kept_skills

    unsupported_claims = unsupported_skills + [
        f"'{keyword}' appears in the rewritten text but not in your original resume"
        for keyword in unsupported_keyword_mentions
    ]

    return {
        "resume": grounded_resume,
        "is_grounded": not unsupported_claims,
        "unsupported_claims": unsupported_claims,
        "removed_skills": unsupported_skills,
        "flagged_keyword_mentions": unsupported_keyword_mentions,
    }
