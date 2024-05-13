from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient
from pydantic import BaseModel, Field

from infrax_node.main import app
from infrax_node.types import App, Job, JobState, Node, NodeState

eth_address = "0x1234567890abcdef"
app_dir = "/tmp/apps"


class TestStore(BaseModel):
    __test__ = False
    node: Node | None = None
    state: NodeState = NodeState.IDLE
    job: Job | None = None
    app_ids: set[str] = Field(default_factory=set)


store = TestStore()


# Test the health check endpoint
@pytest.mark.asyncio
async def test_health_check():
    # Arrange
    client = AsyncClient(app=app, base_url="http://test")

    # Act
    response = await client.get("/__health")

    # Assert
    assert response.status_code == status.HTTP_200_OK


# Parametrized test for installing an app
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "app_id, already_installed, expected_status",
    [
        ("app1", False, status.HTTP_200_OK),  # ID: T1
        ("app2", True, status.HTTP_409_CONFLICT),  # ID: T2
    ],
)
async def test_install_app(app_id, already_installed, expected_status):
    # Arrange
    client = AsyncClient(app=app, base_url="http://test")
    test_app = App(
        id=app_id,
        eth_address=eth_address,
        name="Test App",
        description="A test app",
        meta={},
        spec_id="spec1",
        ts=0,
        last_modified=0,
        files=[],
    )
    store.app_ids = {app_id} if already_installed else set()

    # Act
    with patch("infrax_node.node.install_app") as mock_install:
        response = await client.post(f"/app/{app_id}")

    # Assert
    assert response.status_code == expected_status
    if not already_installed:
        mock_install.assert_called_once_with(test_app)


# Parametrized test for uninstalling an app
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "app_id, is_installed, expected_status",
    [
        ("app1", True, status.HTTP_200_OK),  # ID: T3
        ("app2", False, status.HTTP_404_NOT_FOUND),  # ID: T4
    ],
)
async def test_uninstall_app(app_id, is_installed, expected_status):
    # Arrange
    client = AsyncClient(app=app, base_url="http://test")
    test_app = App(
        id=app_id,
        eth_address=eth_address,
        name="Test App",
        description="A test app",
        meta={},
        spec_id="spec1",
        ts=0,
        last_modified=0,
        files=[],
    )
    store.app_ids = {app_id} if is_installed else set()

    # Act
    with patch("infrax_node.node.uninstall_app") as mock_uninstall:
        response = await client.delete(f"/app/{app_id}")

    # Assert
    assert response.status_code == expected_status
    if is_installed:
        mock_uninstall.assert_called_once_with(test_app)


# Parametrized test for creating a job
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "job_id, app_id, is_app_installed, expected_status",
    [
        ("job1", "app1", True, status.HTTP_201_CREATED),  # ID: T5
        ("job2", "app2", False, status.HTTP_404_NOT_FOUND),  # ID: T6
    ],
)
async def test_create_job(job_id, app_id, is_app_installed, expected_status):
    # Arrange
    client = AsyncClient(app=app, base_url="http://test")
    test_job = Job(
        id=job_id,
        app_id=app_id,
        eth_address=eth_address,
        state=JobState.CREATED,
        ts=0,
        start_ts=None,
        last_modified=0,
    )
    store.app_ids = {app_id} if is_app_installed else set()

    # Act
    with patch("infrax_node.node.run_job") as mock_run_job, patch(
        "infrax_node.types.Job.model_dump", return_value=test_job.model_dump()
    ):
        response = await client.post("/job", json=test_job.model_dump())

    # Assert
    assert response.status_code == expected_status
    assert response.json() == test_job.dict() if is_app_installed else None
    if is_app_installed:
        mock_run_job.assert_called_once_with(test_job)
