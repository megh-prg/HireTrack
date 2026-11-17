from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


def _signup(c, email):
    r = c.post("/api/auth/signup", json={"email": email, "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_endpoints_require_a_token():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        assert c.get("/api/jobs").status_code == 401
        assert c.get("/api/profile").status_code == 401
        assert c.get("/api/progress").status_code == 401


def test_each_user_only_sees_their_own_data():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        alice = _signup(c, "alice@example.com")
        bob = _signup(c, "bob@example.com")

        made = c.post(
            "/api/jobs",
            json={"title": "Alice Job", "company": "A Co", "description": "python fastapi"},
            headers=alice,
        )
        assert made.status_code == 201
        alice_job_id = made.json()["id"]

        c.post(
            "/api/jobs",
            json={"title": "Bob Job", "company": "B Co", "description": "java spring"},
            headers=bob,
        )

        assert [j["title"] for j in c.get("/api/jobs", headers=alice).json()] == ["Alice Job"]
        assert [j["title"] for j in c.get("/api/jobs", headers=bob).json()] == ["Bob Job"]

        # Bob cannot read Alice's job; Alice can.
        assert c.get(f"/api/jobs/{alice_job_id}", headers=bob).status_code == 404
        assert c.get(f"/api/jobs/{alice_job_id}", headers=alice).status_code == 200


def test_each_user_gets_their_own_prep_catalog():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        alice = _signup(c, "a2@example.com")
        bob = _signup(c, "b2@example.com")
        # Alice marks a problem solved; Bob's copy stays untouched.
        alice_problems = c.get("/api/dsa", headers=alice).json()
        assert len(alice_problems) > 0
        pid = alice_problems[0]["id"]
        c.post(f"/api/dsa/{pid}/practice", json={"quality": 5}, headers=alice)
        bob_problems = c.get("/api/dsa", headers=bob).json()
        assert all(p["status"] == "todo" for p in bob_problems)


def test_duplicate_signup_and_login():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        _signup(c, "dup@example.com")
        assert c.post("/api/auth/signup", json={"email": "dup@example.com", "password": "secret123"}).status_code == 409
        assert c.post("/api/auth/login", json={"email": "dup@example.com", "password": "secret123"}).status_code == 200
        assert c.post("/api/auth/login", json={"email": "dup@example.com", "password": "wrongpass"}).status_code == 401
