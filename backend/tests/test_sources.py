from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.jobs import sources
from app.jobs.sources import SourceError, SourceQuery, apply_filters, fetch, parse_careers_url
from app.schemas import JobCreate

GREENHOUSE = {
    "jobs": [
        {
            "id": 1,
            "title": "Backend Engineer - Python",
            "company_name": "Groww",
            "location": {"name": "Bengaluru, India"},
            "absolute_url": "https://job-boards.greenhouse.io/groww/jobs/1",
            "content": "&lt;p&gt;Python, FastAPI and &lt;b&gt;Kafka&lt;/b&gt;&lt;/p&gt;",
            "first_published": "2026-09-01T10:00:00-04:00",
        },
        {
            "id": 2,
            "title": "Assistant Manager - Internal Audit",
            "company_name": "Groww",
            "location": {"name": "Bengaluru, India"},
            "absolute_url": "https://job-boards.greenhouse.io/groww/jobs/2",
            "content": "",
        },
    ]
}
LEVER = [
    {
        "id": "abc",
        "text": "SDE II",
        "categories": {"location": "Bangalore, Karnataka", "team": "Engineering"},
        "workplaceType": "onsite",
        "hostedUrl": "https://jobs.lever.co/meesho/abc",
        "descriptionPlain": "Build services in Go.",
        "lists": [{"text": "Requirements", "content": "<li>Golang, Redis, Kubernetes</li>"}],
        "createdAt": 1757916149833,
    }
]
ASHBY = {
    "jobs": [
        {
            "id": "x1",
            "title": "ML Engineer",
            "location": "Remote",
            "isRemote": True,
            "isListed": True,
            "jobUrl": "https://jobs.ashbyhq.com/sarvam/x1",
            "descriptionPlain": "PyTorch, LLM fine-tuning",
            "publishedAt": "2026-09-10T08:00:00.000+00:00",
            "compensation": {"compensationTierSummary": "₹40L – ₹60L"},
        },
        {"id": "x2", "title": "Hidden", "isListed": False},
    ]
}


def mock_client(routes: dict[str, object]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        for fragment, body in routes.items():
            if fragment in str(request.url):
                return httpx.Response(200, json=body)
        return httpx.Response(404, json={})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_careers_url():
    assert parse_careers_url("https://job-boards.eu.greenhouse.io/groww/jobs/123") == ("greenhouse", "groww")
    assert parse_careers_url("https://boards.greenhouse.io/anthropic") == ("greenhouse", "anthropic")
    assert parse_careers_url("jobs.lever.co/meesho/7d9a") == ("lever", "meesho")
    assert parse_careers_url("https://jobs.ashbyhq.com/sarvam") == ("ashby", "sarvam")
    assert parse_careers_url("https://www.linkedin.com/jobs/view/1") is None


def test_greenhouse_decodes_html_and_extracts_skills():
    jobs = fetch(SourceQuery("greenhouse", "groww"), mock_client({"boards/groww/jobs": GREENHOUSE}))
    assert jobs[0].company == "Groww" and jobs[0].location == "Bengaluru, India"
    assert "<b>Kafka</b>" in jobs[0].description  # decoded; tags are stripped on save


def test_lever_and_ashby_normalisation():
    lever = fetch(SourceQuery("lever", "meesho", company_name="Meesho"), mock_client({"postings/meesho": LEVER}))
    assert lever[0].company == "Meesho" and "Kubernetes" in lever[0].description
    assert lever[0].posted_at.year == 2025

    ashby = fetch(SourceQuery("ashby", "sarvam"), mock_client({"job-board/sarvam": ASHBY}))
    assert [j.title for j in ashby] == ["ML Engineer"]  # unlisted jobs are skipped
    assert ashby[0].remote and ashby[0].salary == "₹40L – ₹60L" and ashby[0].company == "Sarvam"


def test_unknown_slug_raises_helpful_error():
    with pytest.raises(SourceError, match="slug"):
        fetch(SourceQuery("lever", "does-not-exist"), mock_client({}))


def test_adzuna_requires_key():
    with pytest.raises(SourceError, match="developer.adzuna.com"):
        fetch(SourceQuery("adzuna", "python developer", location="Bangalore"), mock_client({}))


def test_adzuna_parsing(monkeypatch):
    settings = sources.get_settings()
    monkeypatch.setattr(settings, "adzuna_app_id", "id")
    monkeypatch.setattr(settings, "adzuna_app_key", "key")
    payload = {
        "results": [
            {
                "id": "9",
                "title": "<strong>Python</strong> Developer",
                "company": {"display_name": "Infosys"},
                "location": {"display_name": "Bangalore, Karnataka"},
                "salary_min": 800000,
                "salary_max": 1200000,
                "redirect_url": "https://www.adzuna.in/details/9",
                "description": "Django, REST APIs",
                "created": "2026-09-20T00:00:00Z",
            }
        ]
    }
    jobs = fetch(SourceQuery("adzuna", "python"), mock_client({"jobs/in/search/1": payload}))
    assert jobs[0].title == "Python Developer" and jobs[0].salary == "₹8–12 LPA"


def test_filters():
    jobs = [
        JobCreate(title="AI Engineer", company="A", location="Bengaluru"),
        JobCreate(title="Account Manager", company="A", location="Bengaluru"),
        JobCreate(title="ML Engineer", company="A", location="San Francisco"),
        JobCreate(title="Backend Engineer", company="A", location="Anywhere", remote=True),
    ]
    kept = apply_filters(jobs, "engineer, developer", "bengaluru, bangalore, india")
    assert [j.title for j in kept] == ["AI Engineer", "Backend Engineer"]
    assert len(apply_filters(jobs, "", "")) == 4
    # Keywords match whole words: "ai" must not match "Maintenance".
    assert apply_filters([JobCreate(title="Maintenance Lead", company="A")], "ai", "") == []


def test_source_api_create_run_and_refresh(client, profile, monkeypatch):
    calls = []

    def fake_fetch(q):
        calls.append(q)
        return fetch(q, mock_client({"boards/groww/jobs": GREENHOUSE}))

    monkeypatch.setattr("app.routers.sources.fetch", fake_fetch)

    created = client.post(
        "/api/sources",
        json={"url": "https://job-boards.greenhouse.io/groww", "title_keywords": "engineer"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["source"]["kind"] == "greenhouse" and body["source"]["query"] == "groww"
    assert (body["found"], body["created"]) == (1, 1)  # audit role filtered out

    job = client.get("/api/jobs").json()[0]
    assert job["source"] == "greenhouse" and "kafka" in job["skills"]
    assert "<" not in job["description"]

    # Refreshing finds nothing new.
    rerun = client.post(f"/api/sources/{body['source']['id']}/run").json()
    assert (rerun["created"], rerun["duplicates"]) == (0, 1)
    assert client.post("/api/sources", json={"url": "https://boards.greenhouse.io/groww"}).status_code == 409

    # Background refresh only touches stale sources.
    from app.database import SessionLocal
    from app.database.models import JobSource
    from app.routers.sources import refresh_stale

    with SessionLocal() as db:
        assert refresh_stale(db, older_than_hours=12) == 0
        src = db.get(JobSource, body["source"]["id"])
        src.last_run_at = datetime.now(timezone.utc) - timedelta(hours=13)
        db.commit()
        assert refresh_stale(db, older_than_hours=12) == 1


def test_source_with_bad_slug_is_not_saved(client, monkeypatch):
    monkeypatch.setattr("app.routers.sources.fetch", lambda q: fetch(q, mock_client({})))
    response = client.post("/api/sources", json={"kind": "lever", "query": "nope"})
    assert response.status_code == 422 and "slug" in response.json()["detail"]
    assert client.get("/api/sources").json() == []
    assert client.post("/api/sources", json={"url": "https://linkedin.com/jobs"}).status_code == 422

