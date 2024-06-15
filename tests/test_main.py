import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from infrax_node.config import config
from infrax_node.main import app
from infrax_node.types import App, Job, Node, NodeState

ETH_ADDRESS = "0x1234567890abcdef"
APP_DIR = "/tmp/apps"
SPEC_ID = "SPEC_ID"
APP_ID = "APP_ID"
NODE_ID = "NODE_ID"


class TestStore(BaseModel):
    __test__ = False
    node: Node | None = None
    state: NodeState = NodeState.IDLE
    job: Job | None = None
    app_ids: set[str] = Field(default_factory=set)


store = TestStore()


def create_node():
    return Node(
        id=NODE_ID,
        eth_address=ETH_ADDRESS,
        state=NodeState.IDLE,
        host="localhost",
        spec_id=SPEC_ID,
        job_id=None,
    )


# Test the health check endpoint
@pytest.mark.asyncio
async def test_health_check():
    # Arrange
    client = TestClient(app=app)

    # Act
    response = client.get("/__health")

    # Assert
    assert response.status_code == status.HTTP_200_OK


# Test the install app endpoint
# when the node is instructed to install an app, it calls the server and requests the
# files for the app, then downloads the files and installs the app into the app directory
# we need to mock the server response and the file download
@pytest.mark.asyncio
async def test_install_app(monkeypatch: pytest.MonkeyPatch):
    store.node = create_node()
    config.host.app_dir = APP_DIR

    def get_app(app_id: str):
        return App(
            id=APP_ID,
            name="Test App",
            description="Test Description",
            meta={},
            spec_id=SPEC_ID,
            ts=0,
            last_modified=0,
            files=[],
            eth_address=ETH_ADDRESS,
        )

    def download_files(files: list[dict], path: str):
        pass

    def set_job_finished(job: Job):
        store.job = None

    def set_job_state(job: Job, state: str):
        pass

    def set_job_finishing(job: Job):
        pass

    def upload_result(result: dict):
        pass

    def set_node_state(state: str):
        pass

    monkeypatch.setattr("infrax_node.crud.get_app", get_app)
    monkeypatch.setattr("infrax_node.node.download_files", download_files)
    monkeypatch.setattr("infrax_node.crud.set_job_finished", set_job_finished)
    monkeypatch.setattr("infrax_node.crud.set_job_state", set_job_state)
    monkeypatch.setattr("infrax_node.crud.set_job_finishing", set_job_finishing)
    monkeypatch.setattr("infrax_node.crud.upload_result", upload_result)
    monkeypatch.setattr("infrax_node.crud.set_node_state", set_node_state)

    client = TestClient(app=app, base_url="http://test")

    # Act
    response = client.post(
        f"/app/{APP_ID}",
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert store.app_ids == {APP_ID}

    # Cleanup
    # clear the test app directory
    import shutil

    shutil.rmtree(APP_DIR)
