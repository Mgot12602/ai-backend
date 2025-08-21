from datetime import datetime
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import pytest

from src.presentation.api.job_routes import router as job_router, get_job_context, JobContext
from src.application.dto import JobResponse


class FakeJobUseCases:
    def __init__(self, jobs_by_id):
        self.jobs_by_id = jobs_by_id

    async def get_job_by_id(self, job_id: str):
        return self.jobs_by_id.get(job_id)


@pytest.fixture
def test_app_owned():
    """App where the current user owns job 'j1'."""
    app = FastAPI()

    owned_job = JobResponse(
        id="j1",
        user_id="user1",
        job_type="text_generation",
        status="pending",
        input_data={"prompt": "hi"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    fake_uc = FakeJobUseCases({"j1": owned_job})

    def override_ctx():
        return JobContext(user_id="user1", use_cases=fake_uc)

    app.dependency_overrides[get_job_context] = override_ctx
    app.include_router(job_router, prefix="/api/v1")

    return app


@pytest.fixture
def test_app_forbidden():
    """App where the current user does NOT own job 'j2'."""
    app = FastAPI()

    other_job = JobResponse(
        id="j2",
        user_id="user2",
        job_type="text_generation",
        status="pending",
        input_data={"prompt": "hi"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    fake_uc = FakeJobUseCases({"j2": other_job})

    def override_ctx():
        return JobContext(user_id="user1", use_cases=fake_uc)

    app.dependency_overrides[get_job_context] = override_ctx
    app.include_router(job_router, prefix="/api/v1")

    return app


@pytest.fixture
def test_app_not_found():
    """App where the job id does not exist."""
    app = FastAPI()

    fake_uc = FakeJobUseCases({})

    def override_ctx():
        return JobContext(user_id="user1", use_cases=fake_uc)

    app.dependency_overrides[get_job_context] = override_ctx
    app.include_router(job_router, prefix="/api/v1")

    return app


def test_get_job_owned_returns_200(test_app_owned):
    client = TestClient(test_app_owned)
    resp = client.get("/api/v1/jobs/j1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "j1"
    assert data["user_id"] == "user1"


def test_get_job_not_owned_returns_403(test_app_forbidden):
    client = TestClient(test_app_forbidden)
    resp = client.get("/api/v1/jobs/j2")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Access denied"


def test_get_job_missing_returns_404(test_app_not_found):
    client = TestClient(test_app_not_found)
    resp = client.get("/api/v1/jobs/j-does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Job not found"
