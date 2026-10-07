import os
import tempfile

import pytest

# Point the app at a throwaway SQLite file *before* app.db creates its engine,
# so the tests never touch the PostgreSQL database.
_db_dir = tempfile.mkdtemp(prefix="taskboard-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # "with" runs the lifespan hook, which creates the tables.
    # A bare TestClient(app) never does, and every DB call fails with "no such table: tasks".
    with TestClient(app) as c:
        yield c


@pytest.fixture
def task(client):
    response = client.post("/api/tasks", json={"title": "Write Helm chart", "priority": "HIGH", "assignee": "Anshul"})
    assert response.status_code == 201
    return response.json()
