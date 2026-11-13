from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from app.database.models import Job, ResumeOptimization
from app.deps import DB, get_or_404, get_profile
from app.optimizer.document import generate_docx_resume, generate_pdf_resume
from app.optimizer.parse import detect_sections, extract_text_from_upload
from app.optimizer.pipeline import optimize_resume_for_job
from app.schemas import OptimizationRead, ResumeIn, ResumeRead

router = APIRouter(prefix="/api", tags=["resume optimizer"])


def _resume_read(resume_text: str) -> ResumeRead:
    sections = detect_sections(resume_text) if resume_text else {"present": [], "missing": []}
    return ResumeRead(
        resume_text=resume_text,
        sections_present=sections["present"],
        sections_missing=sections["missing"],
    )


@router.get("/resume", response_model=ResumeRead, tags=["resume optimizer"])
def get_resume(db: DB):
    return _resume_read(get_profile(db).resume_text)


@router.put("/resume", response_model=ResumeRead)
def save_resume(payload: ResumeIn, db: DB):
    profile = get_profile(db)
    profile.resume_text = payload.resume_text
    db.commit()
    return _resume_read(profile.resume_text)


@router.post("/resume/upload", response_model=ResumeRead)
async def upload_resume(db: DB, file: UploadFile):
    content = await file.read()
    try:
        text = extract_text_from_upload(file.filename or "", file.content_type, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not text:
        raise HTTPException(status_code=400, detail="No text could be extracted from that file.")
    profile = get_profile(db)
    profile.resume_text = text
    db.commit()
    return _resume_read(text)


def _get_optimization(db: DB, job_id: int) -> ResumeOptimization | None:
    return db.scalars(
        select(ResumeOptimization).where(ResumeOptimization.job_id == job_id)
    ).one_or_none()


@router.post("/jobs/{job_id}/optimize", response_model=OptimizationRead)
def optimize(job_id: int, db: DB):
    """Tailor the saved resume to this job: score it, rewrite it (grounded), re-score."""
    job = get_or_404(db, Job, job_id)
    profile = get_profile(db)
    if not profile.resume_text.strip():
        raise HTTPException(status_code=400, detail="Add your resume first (paste it or upload a file).")
    if not job.description.strip():
        raise HTTPException(status_code=400, detail="This job has no description to optimize against.")

    result = optimize_resume_for_job(profile.resume_text, job.description, fallback_keywords=job.skills)

    record = _get_optimization(db, job_id)
    if record is None:
        record = ResumeOptimization(job_id=job_id)
        db.add(record)
    record.score_before = result["score_before"]
    record.score_after = result["score_after"]
    record.missing_keywords = result["missing_keywords"]
    record.optimized_resume = result["optimized_resume"]
    record.unsupported_claims = result["unsupported_claims"]
    record.is_grounded = result["is_grounded"]
    record.ai_available = result["ai_available"]
    db.commit()
    db.refresh(record)
    return record


@router.get("/jobs/{job_id}/optimization", response_model=OptimizationRead)
def get_optimization(job_id: int, db: DB):
    record = _get_optimization(db, job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No optimization yet for this job.")
    return record


@router.get("/jobs/{job_id}/optimization/download")
def download_optimization(job_id: int, db: DB, fmt: str = Query("pdf", pattern="^(pdf|docx)$")):
    record = _get_optimization(db, job_id)
    if record is None or not record.optimized_resume:
        raise HTTPException(status_code=404, detail="No optimized resume to download yet.")
    job = db.get(Job, job_id)
    title = f"Resume - {job.title}" if job else "Optimized Resume"

    if fmt == "docx":
        data = generate_docx_resume(record.optimized_resume, title)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        data = generate_pdf_resume(record.optimized_resume, title)
        media = "application/pdf"

    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="optimized_resume.{fmt}"'},
    )
