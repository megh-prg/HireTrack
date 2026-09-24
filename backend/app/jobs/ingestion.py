"""Pull jobs from external sources, normalise them and insert without duplicates."""

import csv
import hashlib
import html
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Job, Profile
from app.jobs.matching import apply_match
from app.jobs.skills import extract_skills
from app.schemas import JobCreate

_TAG = re.compile(r"<[^>]+>")
_PARENS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def strip_html(text: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text or "", flags=re.I)
    text = html.unescape(_TAG.sub(" ", text))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


def _norm(text: str) -> str:
    return _NON_ALNUM.sub(" ", (text or "").lower()).strip()


def fingerprint(company: str, title: str, location: str) -> str:
    """Stable identity for a posting so the same role from two feeds is stored once.

    Parenthesised noise ("(Remote)", "[Hybrid]") and the word "remote" are ignored.
    """
    title_n = _norm(_PARENS.sub(" ", title)).replace("remote", "").strip()
    company_n = re.sub(r"\b(inc|llc|ltd|pvt|private|limited|technologies|corp)\b", "", _norm(company))
    location_n = _norm(location).replace("remote", "").strip()
    key = "|".join(" ".join(part.split()) for part in (company_n, title_n, location_n))
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class IngestResult:
    created: int = 0
    duplicates: int = 0
    created_ids: list[int] = field(default_factory=list)


def build_job(data: JobCreate, source: str) -> Job:
    description = strip_html(data.description)
    remote = data.remote or "remote" in f"{data.location} {data.title}".lower()
    # Feeds occasionally send very long location lists; clip to the column sizes.
    return Job(
        title=data.title.strip()[:200],
        company=data.company.strip()[:200],
        location=data.location.strip()[:200],
        remote=remote,
        salary=data.salary.strip()[:120],
        url=data.url.strip()[:500],
        description=description,
        skills=extract_skills(f"{data.title}\n{description}\n{' '.join(data.tags)}"),
        source=source,
        external_id=data.external_id[:120] if data.external_id else None,
        fingerprint=fingerprint(data.company, data.title, data.location),
        posted_at=data.posted_at,
    )


def upsert_jobs(db: Session, items: list[JobCreate], source: str) -> IngestResult:
    result = IngestResult()
    profile = db.get(Profile, 1)
    seen: set[str] = set()
    for item in items:
        job = build_job(item, source)
        if job.fingerprint in seen or db.scalar(
            select(Job.id).where(Job.fingerprint == job.fingerprint)
        ):
            result.duplicates += 1
            continue
        seen.add(job.fingerprint)
        if profile:
            apply_match(job, profile)
        db.add(job)
        db.flush()
        result.created += 1
        result.created_ids.append(job.id)
    db.commit()
    return result


# ---------------------------------------------------------------- file uploads


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_upload(filename: str, content: bytes) -> list[JobCreate]:
    """Accept a CSV (header row) or JSON array exported from a spreadsheet or scraper."""
    text = content.decode("utf-8-sig")
    if filename.lower().endswith(".json"):
        rows = json.loads(text)
        if isinstance(rows, dict):
            rows = rows.get("jobs", [])
    else:
        rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(io.StringIO(text))]

    jobs = []
    for row in rows:
        company = row.get("company") or row.get("company_name") or ""
        title = row.get("title") or row.get("role") or ""
        if not (company and title):
            continue
        remote = str(row.get("remote", "")).lower() in {"1", "true", "yes", "y"}
        tags = row.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        jobs.append(
            JobCreate(
                title=title,
                company=company,
                location=row.get("location", ""),
                remote=remote,
                salary=str(row.get("salary", "")),
                url=row.get("url") or row.get("link") or "",
                description=row.get("description", ""),
                tags=tags,
                posted_at=parse_date(row.get("posted_at")),
            )
        )
    return jobs
