from app.optimizer.ats import score_resume_against_jd
from app.optimizer.grounding import ground_optimized_resume
from app.optimizer.pipeline import optimize_resume_for_job, resume_dict_to_text


def test_ats_scores_and_lists_missing_keywords():
    resume = "Experience building APIs in Python and FastAPI.\nSkills: python, fastapi, sql."
    result = score_resume_against_jd(resume, ["python", "fastapi", "docker", "kubernetes"])
    assert 0 <= result["score"] <= 100
    assert "python" in result["matched_keywords"]
    assert "docker" in result["missing_keywords"]
    assert "kubernetes" in result["missing_keywords"]


def test_required_keywords_are_weighted():
    resume = "python developer.\nskills: python."
    result = score_resume_against_jd(
        resume, ["python", "react"], required_keywords=["python"], preferred_keywords=["react"]
    )
    assert result["breakdown"]["required_matched"] == ["python"]
    assert result["breakdown"]["preferred_missing"] == ["react"]


def test_grounding_strips_unsupported_skill():
    original = "I worked with python and sql at my last job."
    optimized = {"summary": "x", "skills": ["python", "sql", "kubernetes"], "experience": [], "projects": []}
    grounded = ground_optimized_resume(original, optimized, ["python", "kubernetes"])
    assert "kubernetes" not in grounded["resume"]["skills"]
    assert grounded["is_grounded"] is False
    assert any("kubernetes" in claim.lower() for claim in grounded["unsupported_claims"])


def test_word_boundary_prevents_java_matching_javascript():
    # "java" must NOT be counted as present just because "javascript" is.
    result = score_resume_against_jd("I write javascript.", ["java"])
    assert "java" in result["missing_keywords"]


def test_pipeline_degrades_without_ai_key():
    # No GEMINI_API_KEY in the test env, so the AI rewrite is skipped but the
    # deterministic score + missing-keyword report still work.
    resume = "Python engineer.\nSkills: python, sql.\nExperience with fastapi."
    result = optimize_resume_for_job(
        resume, "We need a python and docker engineer.", fallback_keywords=["python", "docker"]
    )
    assert result["ai_available"] is False
    assert result["score_before"] >= 0
    assert "docker" in result["missing_keywords"]
    assert result["score_after"] is None
    assert result["optimized_resume"] is None


def test_resume_dict_to_text_flattens_sections():
    text = resume_dict_to_text(
        {"summary": "Dev", "skills": ["python"], "experience": ["Built an API"], "projects": []}
    )
    assert "python" in text.lower()
    assert "built an api" in text.lower()
