import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_teardown_db():
    Base.metadata.create_all(bind=engine)
    yield
    os.remove("test.db")


def test_complete_task():
    # Create a task
    response = client.post(
        "/api/tasks",
        json={"title": "test task", "priority": "medium", "recurrence": "none"},
    )
    assert response.status_code == 200
    task_id = response.json()["id"]

    # Complete the task
    response = client.post(f"/api/tasks/{task_id}/complete")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["success"] is True
    assert response_json["task"]["status"] == "completed"


def test_complete_recurring_task():
    # Create a recurring task
    response = client.post(
        "/api/tasks",
        json={"title": "recurring task", "priority": "high", "recurrence": "daily"},
    )
    assert response.status_code == 200
    task_id = response.json()["id"]

    # Complete the task
    response = client.post(f"/api/tasks/{task_id}/complete")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["success"] is True
    assert response_json["task"]["status"] == "completed"
    assert response_json["is_recurring"] is True
    assert response_json["next_occurrence"] is not None
    assert response_json["next_occurrence"]["parent_task_id"] == task_id
