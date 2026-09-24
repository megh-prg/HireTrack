from datetime import date, timedelta

from app.seed import parse_questions
from app.services.scheduling import next_review

TODAY = date.today()


def test_application_lifecycle(client, profile):
    created = client.post(
        "/api/applications",
        json={"job": {"title": "AI Engineer", "company": "Acme"}, "stage": "applied"},
    )
    assert created.status_code == 201
    app = created.json()
    assert app["applied_on"] == TODAY.isoformat()
    assert app["next_follow_up"] == (TODAY + timedelta(days=7)).isoformat()
    assert [e["to_stage"] for e in app["events"]] == ["applied"]

    moved = client.patch(f"/api/applications/{app['id']}", json={"stage": "technical"}).json()
    assert moved["events"][-1] == {**moved["events"][-1], "from_stage": "applied", "to_stage": "technical"}

    rejected = client.patch(f"/api/applications/{app['id']}", json={"stage": "rejected"}).json()
    assert rejected["next_follow_up"] is None

    progress = client.get("/api/progress").json()
    funnel = {f["stage"]: f["count"] for f in progress["funnel"]}
    assert funnel["applied"] == 1 and funnel["technical"] == 1 and funnel["offer"] == 0
    assert progress["interview_rate"] == 100.0


def test_cannot_track_same_job_twice(client, profile):
    job = client.post("/api/jobs", json={"title": "Dev", "company": "B"}).json()
    assert client.post("/api/applications", json={"job_id": job["id"]}).status_code == 201
    assert client.post("/api/applications", json={"job_id": job["id"]}).status_code == 409
    assert client.post("/api/applications", json={}).status_code == 422


def test_recruiter_status_sets_follow_up(client):
    r = client.post("/api/recruiters", json={"name": "Asha", "company": "C"}).json()
    assert r["next_follow_up"] is None
    r = client.patch(f"/api/recruiters/{r['id']}", json={"status": "contacted"}).json()
    assert r["last_contacted"] == TODAY.isoformat()
    assert r["next_follow_up"] == (TODAY + timedelta(days=5)).isoformat()


def test_followups_include_overdue_and_complete(client, profile):
    app = client.post(
        "/api/applications",
        json={
            "job": {"title": "Dev", "company": "D"},
            "next_follow_up": (TODAY - timedelta(days=2)).isoformat(),
        },
    ).json()
    items = client.get("/api/followups").json()
    assert items[0]["kind"] == "application" and items[0]["overdue_days"] == 2

    assert client.post(f"/api/followups/application/{app['id']}/complete", json={"reschedule_days": 30}).status_code == 204
    assert client.get("/api/followups").json() == []


def test_spaced_repetition():
    assert next_review(1, 4, TODAY) == (0, TODAY + timedelta(days=1))
    assert next_review(5, 0, TODAY) == (1, TODAY + timedelta(days=1))
    assert next_review(5, 2, TODAY) == (3, TODAY + timedelta(days=7))
    assert next_review(3, 2, TODAY) == (3, TODAY + timedelta(days=3))


def test_dsa_practice_flow(client):
    problems = client.get("/api/dsa").json()
    assert len(problems) >= 50  # seeded from prep/dsa/problems.csv
    pid = problems[0]["id"]
    for _ in range(3):
        p = client.post(f"/api/dsa/{pid}/practice", json={"quality": 5}).json()
    assert p["status"] == "mastered" and p["attempts"] == 3
    p = client.post(f"/api/dsa/{pid}/practice", json={"quality": 1}).json()
    assert p["status"] == "attempted" and p["review_streak"] == 0
    progress = client.get("/api/progress").json()
    assert progress["weekly_goals"][1]["done"] == 4
    assert progress["practice_streak_days"] == 1


def test_prep_seed_review_and_recommendations(client, profile):
    tracks = {t["track"]: t for t in client.get("/api/prep/tracks").json()}
    assert all(tracks[t]["total"] >= 10 for t in ("python", "sql", "backend", "genai", "system-design"))

    qid = client.get("/api/prep/questions", params={"track": "sql"}).json()[0]["id"]
    q = client.post(f"/api/prep/questions/{qid}/review", json={"quality": 4}).json()
    assert q["confidence"] == 4 and q["next_review"] == (TODAY + timedelta(days=1)).isoformat()
    assert client.get("/api/prep/tracks").json()[1]["reviewed"] == 1

    # A gap in Kafka (system-design track) should put system-design questions first.
    client.post("/api/jobs", json={"title": "AI Engineer", "company": "K", "location": "Bengaluru", "description": "Python Kafka"})
    recommended = client.get("/api/prep/recommended").json()
    assert recommended[0]["track"] == "system-design"

    custom = client.post("/api/prep/questions", json={"track": "genai", "question": "What is RLHF?"})
    assert custom.status_code == 201 and custom.json()["source"] == "user"


def test_parse_questions():
    md = "# T\n\n## Q1?\nTags: a, b\n\nAnswer one.\n\n## Q2\nAnswer two\n"
    assert parse_questions(md) == [
        {"question": "Q1?", "answer": "Answer one.", "tags": ["a", "b"]},
        {"question": "Q2", "answer": "Answer two", "tags": []},
    ]
