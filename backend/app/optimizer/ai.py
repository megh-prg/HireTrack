"""Gemini-backed resume/JD language tasks.

Ported from the standalone resume optimizer and made synchronous so it fits
HireTrack's plain (non-async) routers. Every call raises AIServiceUnavailable
when no key is configured or the API errors, so callers can degrade gracefully
instead of treating a fallback as a real answer.
"""

import json
import logging

import google.genai as genai

from app.config import get_settings

logger = logging.getLogger("hiretrack.optimizer")
_settings = get_settings()

_client: genai.Client | None = None
if _settings.gemini_api_key:
    # Pin the API version: the "-latest" flash models live on v1beta, and newer
    # google-genai releases default to v1 (where they 404).
    _client = genai.Client(
        api_key=_settings.gemini_api_key,
        http_options={"api_version": "v1beta"},
    )


class AIServiceUnavailable(RuntimeError):
    """Gemini isn't configured or the call failed."""


def ai_available() -> bool:
    return _client is not None


def stringify_resume_item(item) -> str:
    """Flatten a resume list entry to plain text.

    The prompt asks Gemini for flat strings under experience/projects, but it
    sometimes returns structured objects instead; callers that join() these
    lists need a plain string either way.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return " - ".join(str(v) for v in item.values() if v)
    if isinstance(item, list):
        return "; ".join(stringify_resume_item(sub) for sub in item)
    return "" if item is None else str(item)


OPTIMIZE_PROMPT = """
You are an AI resume optimization assistant. Analyze the resume text and the job description.
Return a valid JSON object with keys: summary, skills, experience, projects.
Do not create or invent any experience not present in the resume. Preserve truth and keep the resume ATS-friendly.

Respond only with JSON.

Resume:
{resume_text}

Job Description:
{job_description}
"""

JD_ANALYSIS_PROMPT = """
You are an expert ATS recruiter. Analyze the following job description and extract its key requirements.
Distinguish between skills that are explicitly required/mandatory and skills that are listed as
preferred/nice-to-have/bonus. If the job description doesn't separate them explicitly, use your judgment
based on the language used (e.g. "must have", "required" vs. "nice to have", "a plus", "bonus").

Return a valid JSON object exactly matching this schema:
{{
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill3"],
  "tools": ["tool1", "tool2"],
  "roles": ["role1", "role2"]
}}

Ensure the lists are concise and highly relevant. Return only JSON.

Job Description:
{job_description}
"""


def _generate_json(prompt: str) -> dict:
    if _client is None:
        raise AIServiceUnavailable("Gemini is not configured (set GEMINI_API_KEY).")
    try:
        response = _client.models.generate_content(
            model=_settings.gemini_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except Exception as exc:  # network error, quota, bad JSON, ...
        logger.exception("Gemini call failed")
        raise AIServiceUnavailable(str(exc)) from exc


def extract_jd_keywords(job_description: str) -> dict:
    data = _generate_json(JD_ANALYSIS_PROMPT.format(job_description=job_description))
    data.setdefault("required_skills", [])
    data.setdefault("preferred_skills", [])
    data.setdefault("tools", [])
    data.setdefault("roles", [])
    return data


def generate_optimized_resume(resume_text: str, job_description: str) -> dict:
    return _generate_json(OPTIMIZE_PROMPT.format(resume_text=resume_text, job_description=job_description))
