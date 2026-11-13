"""Turn a job description into required/preferred skill lists.

Wraps the Gemini call and degrades to an empty keyword set if the AI is
unavailable, so a transient outage never crashes the optimize flow.
"""

import logging

from app.optimizer.ai import AIServiceUnavailable, extract_jd_keywords

logger = logging.getLogger("hiretrack.optimizer")


def analyze_job_description(jd_text: str) -> dict:
    ai_degraded = False
    try:
        ai_result = extract_jd_keywords(jd_text)
    except AIServiceUnavailable:
        logger.warning("JD keyword extraction unavailable; using empty keyword set")
        ai_result = {"required_skills": [], "preferred_skills": [], "tools": [], "roles": []}
        ai_degraded = True

    required_skills = [str(s).lower() for s in ai_result.get("required_skills", [])]
    preferred_skills = [str(s).lower() for s in ai_result.get("preferred_skills", [])]
    tools = [str(t).lower() for t in ai_result.get("tools", [])]
    roles = [str(r).lower() for r in ai_result.get("roles", [])]

    skills = list({*required_skills, *preferred_skills})
    keyword_set = list({*skills, *tools, *roles})
    return {
        "keywords": sorted(keyword_set),
        "skills": skills,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "tools": tools,
        "roles": roles,
        "ai_degraded": ai_degraded,
    }
