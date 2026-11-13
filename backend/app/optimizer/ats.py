"""Deterministic ATS scoring of a resume against a job description's keywords.

Pure Python, no LLM call and no external services, so the score is explainable
and stable: the same resume and keywords always produce the same number.
"""

import re
from typing import Any

SECTION_KEYWORDS = [
    "experience",
    "education",
    "skills",
    "projects",
    "summary",
    "certifications",
    "professional experience",
    "work history",
]


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", " ", text.lower())


def _contains_keyword(normalized_text: str, keyword: str) -> bool:
    """Word-boundary keyword check.

    Plain substring matching (``keyword in normalized_text``) gives false
    positives like "java" matching inside "javascript", which silently
    inflates ATS scores. ``\\b`` anchors the match to whole word/phrase
    boundaries instead.
    """
    return re.search(rf"\b{re.escape(keyword)}\b", normalized_text) is not None


def _keyword_match_score(resume_text: str, keywords: list[str]) -> tuple[float, list[str], list[str]]:
    normalized_resume = _normalize_text(resume_text)
    found = [k for k in keywords if k and _contains_keyword(normalized_resume, k)]
    missing = [k for k in keywords if k and not _contains_keyword(normalized_resume, k)]
    score = len(found) / max(len(keywords), 1) * 100
    return score, found, missing


def _weighted_keyword_score(
    resume_text: str,
    required_keywords: list[str],
    preferred_keywords: list[str],
) -> dict[str, Any]:
    """Score keyword coverage, weighting required skills above preferred ones.

    A resume that covers every required skill but no preferred ones should
    score much higher than one that covers only preferred skills -- a flat
    keyword match treats both the same, which misrepresents fit.
    """
    normalized_resume = _normalize_text(resume_text)
    required = [k for k in required_keywords if k]
    preferred = [k for k in preferred_keywords if k]

    required_matched = [k for k in required if _contains_keyword(normalized_resume, k)]
    required_missing = [k for k in required if not _contains_keyword(normalized_resume, k)]
    preferred_matched = [k for k in preferred if _contains_keyword(normalized_resume, k)]
    preferred_missing = [k for k in preferred if not _contains_keyword(normalized_resume, k)]

    required_ratio = len(required_matched) / len(required) if required else 1.0
    if preferred:
        preferred_ratio = len(preferred_matched) / len(preferred)
        score = required_ratio * 70 + preferred_ratio * 30
    else:
        score = required_ratio * 100

    return {
        "score": score,
        "matched": required_matched + preferred_matched,
        "missing": required_missing + preferred_missing,
        "required_matched": required_matched,
        "required_missing": required_missing,
        "preferred_matched": preferred_matched,
        "preferred_missing": preferred_missing,
    }


def _section_presence_score(resume_text: str) -> tuple[float, list[str]]:
    normalized = _normalize_text(resume_text)
    present = [s for s in SECTION_KEYWORDS if s in normalized]
    score = min(len(present) / len(SECTION_KEYWORDS), 1.0) * 100
    weak = [s for s in SECTION_KEYWORDS if s not in normalized]
    return score, weak


def _formatting_score(resume_text: str) -> float:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    bullet_count = sum(1 for line in lines if line.startswith(("-", "*", "•")))
    avg_length = sum(len(line) for line in lines) / max(len(lines), 1)
    bullet_score = min(bullet_count / 15, 1.0)
    length_score = 1.0 if 60 < avg_length < 160 else 0.6
    return (bullet_score * 0.7 + length_score * 0.3) * 100


def _relevance_score(resume_text: str, keywords: list[str]) -> float:
    normalized = _normalize_text(resume_text)
    words = normalized.split()
    total_words = len(words)
    if total_words == 0 or not keywords:
        return 0.0

    total_occurrences = sum(normalized.count(k) for k in keywords if k)
    density = total_occurrences / total_words

    # Target density is 2%-4%. Above 5% is keyword stuffing.
    if density > 0.05:
        return max(0.0, 100 - ((density - 0.05) * 2000))
    return min(density / 0.03, 1.0) * 100


def score_resume_against_jd(
    resume_text: str,
    keywords: list[str],
    required_keywords: list[str] | None = None,
    preferred_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Score a resume against a job description's keywords (0-100).

    When ``required_keywords`` is given, keyword coverage is weighted so that
    matching required skills matters more than preferred ones. Otherwise falls
    back to a flat keyword match over ``keywords``.
    """
    extra_breakdown: dict[str, Any] = {}
    if required_keywords:
        weighted = _weighted_keyword_score(resume_text, required_keywords, preferred_keywords or [])
        keyword_score = weighted["score"]
        matched_keywords = weighted["matched"]
        missing_keywords = weighted["missing"]
        extra_breakdown = {
            "required_matched": weighted["required_matched"],
            "required_missing": weighted["required_missing"],
            "preferred_matched": weighted["preferred_matched"],
            "preferred_missing": weighted["preferred_missing"],
        }
    else:
        keyword_score, matched_keywords, missing_keywords = _keyword_match_score(resume_text, keywords)

    section_score, weak_sections = _section_presence_score(resume_text)
    formatting_score = _formatting_score(resume_text)
    relevance_score = _relevance_score(resume_text, keywords)

    final_score = (
        keyword_score * 0.50
        + section_score * 0.20
        + formatting_score * 0.15
        + relevance_score * 0.15
    )

    return {
        "score": round(final_score, 1),
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "weak_sections": weak_sections,
        "breakdown": {
            "keyword_match": round(keyword_score, 1),
            "section_presence": round(section_score, 1),
            "formatting": round(formatting_score, 1),
            "relevance": round(relevance_score, 1),
            **extra_breakdown,
        },
    }
