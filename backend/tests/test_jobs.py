import httpx

from app.jobs.ingestion import fetch_remotive, fingerprint, parse_upload, strip_html
from app.jobs.skills import canonicalize, extract_skills


def test_extract_skills_is_boundary_aware():
    text = "We use PostgreSQL, Node.js, C++ and RESTful APIs; experience with LLMs and pgvector."
    skills = extract_skills(text)
    assert {"postgresql", "node.js", "c++", "rest api", "llm", "vector databases"} <= set(skills)
    assert "sql" not in skills  # must not fire inside "PostgreSQL"
    assert "java" not in extract_skills("JavaScript developer")


def test_canonicalize_keeps_unknown_skills():
    assert canonicalize(["Postgres", "LLMs", "Airtable"]) == ["postgresql", "llm", "airtable"]


def test_fingerprint_ignores_noise():
    a = fingerprint("Acme Technologies Pvt Ltd", "Python Engineer (Remote)", "Remote")
    b = fingerprint("ACME", "Python Engineer", "")
    assert a == b


def test_strip_html():
    assert strip_html("<p>Hello&nbsp;<b>world</b></p><ul><li>one</li></ul>") == "Hello\xa0 world \n one"


def test_create_job_scores_and_rejects_duplicates(client, profile):
    job = {
        "title": "AI Engineer",
        "company": "Acme",
        "location": "Bengaluru",
        "description": "Python, FastAPI, PostgreSQL, RAG with LangChain, Kubernetes",
    }
    first = client.post("/api/jobs", json=job)
    assert first.status_code == 201
    body = first.json()
    assert body["match_score"] > 70
    assert "langchain" in body["missing_skills"]
    assert "fastapi" in body["matched_skills"]

    dup = client.post("/api/jobs", json={**job, "title": "AI Engineer (Remote)"})
    assert dup.status_code == 409


def test_senior_roles_are_penalised_for_juniors(client, profile):
    base = {"company": "X", "location": "Bengaluru", "description": "Python FastAPI Docker"}
    junior = client.post("/api/jobs", json={**base, "title": "Python Backend Engineer"}).json()
    senior = client.post(
        "/api/jobs", json={**base, "company": "Y", "title": "Senior Python Backend Engineer"}
    ).json()
    assert senior["match_score"] < junior["match_score"]


def test_upload_csv(client, profile):
    csv_text = "Title,Company,Location,Description\nGenAI Engineer,Foo,Remote,RAG and embeddings\n,Bad,,\n"
    response = client.post("/api/jobs/upload", files={"file": ("jobs.csv", csv_text, "text/csv")})
    assert response.status_code == 200
    assert response.json()["created"] == 1
    jobs = client.get("/api/jobs").json()
    assert jobs[0]["remote"] is True
    assert jobs[0]["source"] == "upload"


def test_parse_upload_json():
    jobs = parse_upload("x.json", b'{"jobs": [{"role": "Dev", "company_name": "Z", "tags": "python, sql"}]}')
    assert jobs[0].title == "Dev" and jobs[0].tags == ["python", "sql"]


def test_fetch_remotive_with_mock_transport(client, profile, monkeypatch):
    payload = {
        "jobs": [
            {
                "id": 1,
                "title": "Python Developer",
                "company_name": "Remote Co",
                "candidate_required_location": "India",
                "url": "https://remotive.com/1",
                "description": "<p>Python, FastAPI and AWS</p>",
                "tags": ["python"],
                "publication_date": "2026-09-01T10:00:00",
            }
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    jobs = fetch_remotive("python", client=httpx.Client(transport=transport))
    assert jobs[0].company == "Remote Co" and jobs[0].remote

    monkeypatch.setattr("app.routers.jobs.fetch_remotive", lambda search, limit: jobs)
    first = client.post("/api/jobs/ingest/remotive", json={"search": "python"}).json()
    second = client.post("/api/jobs/ingest/remotive", json={"search": "python"}).json()
    assert (first["created"], second["duplicates"]) == (1, 1)


def test_analyze_and_skill_gaps(client, profile):
    result = client.post(
        "/api/matching/analyze",
        json={"title": "AI Engineer", "description": "Python, RAG, Kafka and Kubernetes", "location": "Remote"},
    ).json()
    assert set(result["missing_skills"]) == {"kafka", "kubernetes"}

    client.post(
        "/api/jobs",
        json={"title": "AI Engineer", "company": "A", "location": "Bengaluru", "description": "Python RAG Kafka"},
    )
    gaps = client.get("/api/matching/skill-gaps").json()
    assert gaps[0] == {"skill": "kafka", "jobs": 1, "track": "system-design"}

    matches = client.get("/api/matching", params={"min_score": 0}).json()
    assert len(matches) == 1


def test_profile_update_rescores_jobs(client, profile):
    job = client.post(
        "/api/jobs", json={"title": "AI Engineer", "company": "A", "description": "Kafka"}
    ).json()
    assert "kafka" in job["missing_skills"]
    client.put("/api/profile", json={**profile, "skills": profile["skills"] + ["Kafka"]})
    assert client.get(f"/api/jobs/{job['id']}").json()["missing_skills"] == []


def test_location_fit_for_remote_and_onsite():
    from app.database.models import Profile
    from app.jobs.matching import location_fit

    p = Profile(locations=["Bengaluru", "Remote India"], open_to_remote=True)
    assert location_fit("Remote", True, p) == 1.0
    assert location_fit("Worldwide", True, p) == 1.0
    assert location_fit("India", True, p) == 1.0
    assert location_fit("USA only", True, p) == 0.4
    assert location_fit("Bengaluru, Karnataka", False, p) == 1.0
    assert location_fit("Pune", False, p) == 0.0
    assert location_fit("", False, p) == 0.3
