"""Real job sources.

Every fetcher returns normalised `JobCreate` items; saving and de-duplication happen in
`ingestion.upsert_jobs`. All sources are official public APIs (no scraping):

- greenhouse / lever / ashby: a company's own careers board (the ATS behind most
  startup career pages). Point at the company's slug, e.g. jobs.lever.co/<slug>.
- adzuna: aggregated listings for India (needs a free API key, developer.adzuna.com).
- remotive: remote-only roles worldwide.
"""

import html
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.jobs.ingestion import parse_date
from app.schemas import JobCreate

SOURCE_KINDS = ("greenhouse", "lever", "ashby", "adzuna", "remotive")
USER_AGENT = "HireTrack/2.0 (personal job tracker)"


class SourceError(Exception):
    """A source could not be fetched (bad slug, missing key, upstream down)."""


@dataclass
class SourceQuery:
    kind: str
    query: str  # company slug for ATS boards, search keywords for adzuna/remotive
    location: str = ""  # adzuna "where"
    company_name: str = ""  # display name override (Lever/Ashby don't return one)
    limit: int = 100


def _get(client: httpx.Client, url: str, **params) -> dict | list:
    try:
        response = client.get(url, params=params or None, headers={"User-Agent": USER_AGENT})
    except httpx.HTTPError as exc:
        raise SourceError(f"Could not reach {urlparse(url).netloc}: {exc}") from exc
    if response.status_code == 404:
        raise SourceError("Not found — check the company slug in the careers-page URL")
    if response.status_code in (401, 403):
        raise SourceError("The source rejected the request (check API keys)")
    if response.is_error:
        raise SourceError(f"{urlparse(url).netloc} returned HTTP {response.status_code}")
    return response.json()


def _title_case(slug: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_]", slug) if part)


def _from_ms(ms: int | None) -> date | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date() if ms else None


def _is_remote(*values: str | None) -> bool:
    return any(v and "remote" in v.lower() for v in values)


# ---------------------------------------------------------------- fetchers


def fetch_greenhouse(q: SourceQuery, client: httpx.Client) -> list[JobCreate]:
    base = f"https://boards-api.greenhouse.io/v1/boards/{q.query}"
    payload = _get(client, f"{base}/jobs", content="true")
    jobs = []
    for raw in payload.get("jobs", []):
        location = (raw.get("location") or {}).get("name", "")
        jobs.append(
            JobCreate(
                title=raw.get("title", ""),
                company=q.company_name or raw.get("company_name") or _title_case(q.query),
                location=location,
                remote=_is_remote(location),
                url=raw.get("absolute_url", ""),
                # Greenhouse double-encodes its HTML (&lt;p&gt;), so decode before stripping tags.
                description=html.unescape(raw.get("content") or ""),
                external_id=str(raw.get("id")),
                posted_at=parse_date(raw.get("first_published") or raw.get("updated_at")),
            )
        )
    return jobs


def fetch_lever(q: SourceQuery, client: httpx.Client) -> list[JobCreate]:
    payload = _get(client, f"https://api.lever.co/v0/postings/{q.query}", mode="json")
    if not isinstance(payload, list):
        raise SourceError("Unexpected response from Lever")
    jobs = []
    for raw in payload:
        cats = raw.get("categories") or {}
        location = cats.get("location") or ", ".join(cats.get("allLocations") or [])
        sections = " ".join(f"{s.get('text', '')}\n{s.get('content', '')}" for s in raw.get("lists") or [])
        salary = raw.get("salaryRange") or {}
        jobs.append(
            JobCreate(
                title=raw.get("text", ""),
                company=q.company_name or _title_case(q.query),
                location=location,
                remote=raw.get("workplaceType") == "remote" or _is_remote(location),
                salary=f"{salary.get('currency', '')} {salary.get('min', '')}–{salary.get('max', '')}".strip()
                if salary.get("min")
                else "",
                url=raw.get("hostedUrl", ""),
                description=f"{raw.get('descriptionPlain', '')}\n{sections}\n{raw.get('additionalPlain', '')}",
                tags=[t for t in (cats.get("team"), cats.get("department")) if t],
                external_id=raw.get("id"),
                posted_at=_from_ms(raw.get("createdAt")),
            )
        )
    return jobs


def fetch_ashby(q: SourceQuery, client: httpx.Client) -> list[JobCreate]:
    payload = _get(
        client, f"https://api.ashbyhq.com/posting-api/job-board/{q.query}", includeCompensation="true"
    )
    jobs = []
    for raw in payload.get("jobs", []):
        if raw.get("isListed") is False:
            continue
        compensation = (raw.get("compensation") or {}).get("compensationTierSummary") or ""
        location = raw.get("location") or ""
        jobs.append(
            JobCreate(
                title=raw.get("title", ""),
                company=q.company_name or _title_case(q.query),
                location=location,
                remote=bool(raw.get("isRemote")) or raw.get("workplaceType") == "Remote",
                salary=compensation,
                url=raw.get("jobUrl", ""),
                description=raw.get("descriptionPlain") or raw.get("descriptionHtml") or "",
                tags=[t for t in (raw.get("department"), raw.get("team")) if t],
                external_id=raw.get("id"),
                posted_at=parse_date(raw.get("publishedAt")),
            )
        )
    return jobs


def _lpa(value: float | None) -> str:
    return f"{value / 100_000:.1f}".rstrip("0").rstrip(".") if value else ""


def fetch_adzuna(q: SourceQuery, client: httpx.Client) -> list[JobCreate]:
    settings = get_settings()
    if not (settings.adzuna_app_id and settings.adzuna_app_key):
        raise SourceError(
            "Adzuna needs a free API key: sign up at developer.adzuna.com, then set "
            "ADZUNA_APP_ID and ADZUNA_APP_KEY in backend/.env (or docker-compose) and restart."
        )
    jobs: list[JobCreate] = []
    per_page = 50
    for page in range(1, max(1, q.limit // per_page) + 1):
        payload = _get(
            client,
            f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/{page}",
            app_id=settings.adzuna_app_id,
            app_key=settings.adzuna_app_key,
            what=q.query,
            where=q.location or None,
            results_per_page=per_page,
            sort_by="date",
        )
        results = payload.get("results", [])
        for raw in results:
            low, high = _lpa(raw.get("salary_min")), _lpa(raw.get("salary_max"))
            location = (raw.get("location") or {}).get("display_name", "")
            jobs.append(
                JobCreate(
                    title=html.unescape(re.sub(r"<[^>]+>", "", raw.get("title", ""))),
                    company=(raw.get("company") or {}).get("display_name", ""),
                    location=location,
                    remote=_is_remote(location, raw.get("title")),
                    salary=f"₹{low}–{high} LPA" if low and high and low != high else (f"₹{low} LPA" if low else ""),
                    url=raw.get("redirect_url", ""),
                    # Adzuna only returns a snippet; the full text is on the linked page.
                    description=raw.get("description", ""),
                    external_id=str(raw.get("id", "")),
                    posted_at=parse_date(raw.get("created")),
                )
            )
        if len(results) < per_page:
            break
    return jobs


def fetch_remotive(q: SourceQuery, client: httpx.Client) -> list[JobCreate]:
    """Remote roles from Remotive. Their terms: link back to postings, poll a few times a day at most."""
    payload = _get(client, get_settings().remotive_url, search=q.query, limit=q.limit)
    return [
        JobCreate(
            title=raw.get("title", ""),
            company=raw.get("company_name", ""),
            location=raw.get("candidate_required_location") or "Remote",
            remote=True,
            salary=raw.get("salary") or "",
            url=raw.get("url", ""),
            description=raw.get("description", ""),
            tags=raw.get("tags") or [],
            external_id=str(raw.get("id", "")),
            posted_at=parse_date(raw.get("publication_date")),
        )
        for raw in payload.get("jobs", [])[: q.limit]
    ]


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "adzuna": fetch_adzuna,
    "remotive": fetch_remotive,
}


def fetch(q: SourceQuery, client: httpx.Client | None = None) -> list[JobCreate]:
    owns_client = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        jobs = FETCHERS[q.kind](q, client)
    finally:
        if owns_client:
            client.close()
    return [j for j in jobs if j.title.strip() and j.company.strip()]


# ---------------------------------------------------------------- helpers

_CAREERS_URL = [
    ("greenhouse", re.compile(r"(?:job-)?boards(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)")),
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/([\w-]+)")),
    ("lever", re.compile(r"jobs(?:\.eu)?\.lever\.co/([\w-]+)")),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)")),
]


def parse_careers_url(url: str) -> tuple[str, str] | None:
    """jobs.lever.co/meesho/... -> ("lever", "meesho")."""
    for kind, pattern in _CAREERS_URL:
        if match := pattern.search(url):
            return kind, match.group(1)
    return None


def _keywords(text: str) -> list[str]:
    return [k.strip().lower() for k in text.split(",") if k.strip()]


def apply_filters(jobs: list[JobCreate], title_keywords: str, location_keywords: str) -> list[JobCreate]:
    """Company boards list every opening (sales, finance…); keep only the ones you care about.

    A job passes if its title contains any title keyword, and its location contains any
    location keyword (remote jobs pass the location filter). Empty filters let everything through.
    """
    titles, places = _keywords(title_keywords), _keywords(location_keywords)

    def title_ok(job: JobCreate) -> bool:
        title = job.title.lower()
        return not titles or any(re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", title) for k in titles)

    def place_ok(job: JobCreate) -> bool:
        return not places or job.remote or any(p in job.location.lower() for p in places)

    return [j for j in jobs if title_ok(j) and place_ok(j)]
