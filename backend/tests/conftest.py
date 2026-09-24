import os
import tempfile
from pathlib import Path

# Configure an isolated database before the app (and its engine) is imported.
# CI sets TEST_DATABASE_URL to a PostgreSQL service; locally a temp SQLite file is used.
_tmp = Path(tempfile.mkdtemp(prefix="hiretrack-test-"))
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp / 'test.db'}"
os.environ["SEED_DEMO_DATA"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:  # runs lifespan: create tables + seed prep content
        yield test_client


@pytest.fixture()
def profile(client):
    payload = {
        "name": "Test",
        "target_roles": ["AI Engineer", "Python Backend Engineer"],
        "locations": ["Bengaluru"],
        "open_to_remote": True,
        "skills": ["Python", "FastAPI", "Postgres", "Docker", "RAG", "LLMs"],
        "experience_years": 2,
        "salary_expectation": "",
        "weekly_application_goal": 10,
        "weekly_dsa_goal": 5,
        "weekly_outreach_goal": 5,
    }
    response = client.put("/api/profile", json=payload)
    assert response.status_code == 200
    return response.json()
