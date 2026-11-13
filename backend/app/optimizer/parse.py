"""Extract plain text from an uploaded PDF or DOCX resume."""

import io
import re

from docx import Document
from pypdf import PdfReader

from app.config import get_settings

CANONICAL_SECTIONS = [
    "summary",
    "experience",
    "education",
    "skills",
    "projects",
    "certifications",
]


def extract_text_from_upload(filename: str, content_type: str | None, content: bytes) -> str:
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise ValueError(f"File exceeds the {limit_mb}MB upload limit.")

    name = (filename or "").lower()

    if name.endswith(".pdf") or content_type == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception as exc:
            raise ValueError("Could not parse PDF file.") from exc

    if name.endswith(".docx") or content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        try:
            document = Document(io.BytesIO(content))
            return "\n".join(p.text for p in document.paragraphs if p.text).strip()
        except Exception as exc:
            raise ValueError("Could not parse DOCX file.") from exc

    raise ValueError("Unsupported file type. Upload a PDF or DOCX resume.")


def detect_sections(text: str) -> dict[str, list[str]]:
    """Deterministically check which canonical resume sections are present."""
    normalized = re.sub(r"[^a-z0-9\s]+", " ", text.lower())
    present = [s for s in CANONICAL_SECTIONS if s in normalized]
    missing = [s for s in CANONICAL_SECTIONS if s not in normalized]
    return {"present": present, "missing": missing}
