import httpx
from loguru import logger
from pydantic import BaseModel

from .config import config
from .exceptions import (
    AppFailedToInstallException,
    AppFailedToUninstallException,
    NodeNotFoundException,
    NodeRegistrationFailureException,
)
from .store import store
from .types import App, Config, Job, JobState, Node, NodeDef, NodeState, Result


class RegisterDTO(BaseModel):
    port: int
    node: NodeDef


class AppErrorReportDTO(BaseModel):
    error: str
    type: str = "INSTALL_ERROR"


def register(config: Config) -> None:
    transport = httpx.HTTPTransport(retries=3, verify=False)
    with httpx.Client(transport=transport) as client:
        response = client.post(
            f"{config.router_url}/node",
            headers={"ethaddress": config.node.eth_address},
            json=RegisterDTO(
                port=config.host.external_port,
                node=config.node,
            ).model_dump(),
            timeout=10,
            follow_redirects=True,
        )
        if response.status_code != 201:
            logger.error("Failed to register with router")
            raise NodeRegistrationFailureException("Failed to register with router")
        node = Node(**response.json())
        store.node = node
    logger.info(f"Registered with router successfully. Node ID: {node.id}")


def set_job_finishing(job: Job) -> None:
    set_job_state(job, JobState.FINISHING)


def set_job_finished(job: Job) -> None:
    set_job_state(job, JobState.FINISHED)


def set_job_state(job: Job, state: JobState) -> None:
    job.state = state
    response = httpx.put(
        f"{config.router_url}/job/{job.id}",
        headers={"ethaddress": config.node.eth_address},
        json=job.model_dump(),
    )
    response.raise_for_status()
    logger.info(f"Job {job.id} state set to {state.name}")


def upload_result(result: Result) -> None:
    response = httpx.post(
        f"{config.router_url}/job/{result.job_id}/result",
        headers={"ethaddress": config.node.eth_address},
        json=result.model_dump(),
    )
    response.raise_for_status()
    logger.info(f"Result for job {result.job_id} uploaded")


def report_failed_app_install(app: App, error: AppFailedToInstallException) -> None:
    app_error_report_dto = AppErrorReportDTO(error=str(error), type="INSTALL_ERROR")
    response = httpx.put(
        f"{config.router_url}/app/{app.id}",
        headers={"ethaddress": config.node.eth_address},
        json=app_error_report_dto.model_dump(),
    )
    response.raise_for_status()
    logger.error(f"Failed to install app {app.id}: {error}")


def report_failed_app_uninstall(app: App, error: AppFailedToUninstallException) -> None:
    app_error_report_dto = AppErrorReportDTO(error=str(error), type="UNINSTALL_ERROR")
    response = httpx.put(
        f"{config.router_url}/app/{app.id}",
        headers={"ethaddress": config.node.eth_address},
        json=app_error_report_dto.model_dump(),
    )
    response.raise_for_status()
    logger.error(f"Failed to install app {app.id}: {error}")


def set_node_busy() -> None:
    set_node_state(NodeState.BUSY)


def set_node_idle() -> None:
    set_node_state(NodeState.IDLE)


def set_node_state(state: NodeState) -> None:
    class NodeStateDTO(BaseModel):
        node_id: str
        state: NodeState

    if not store.node:
        raise NodeNotFoundException("Node not found")
    store.state = state
    logger.info(f"Node state set to {state.name}")
    node_state_dto = NodeStateDTO(node_id=store.node.id, state=state)
    response = httpx.put(
        f"{config.router_url}/node/state",
        headers={"ethaddress": config.node.eth_address},
        json=node_state_dto.model_dump(),
    )
    response.raise_for_status()


def add_app(app: App) -> None:
    if not store.node:
        raise NodeNotFoundException("Node not found")
    response = httpx.put(
        f"{config.router_url}/node/{store.node.id}/app/{app.id}",
        headers={"ethaddress": config.node.eth_address},
    )
    response.raise_for_status()
    logger.info(f"App {app.id} added to node {store.node.id}")


def remove_app(app: App) -> None:
    if not store.node:
        raise NodeNotFoundException("Node not found")
    response = httpx.delete(
        f"{config.router_url}/node/{store.node.id}/app/{app.id}",
        headers={"ethaddress": config.node.eth_address},
    )
    response.raise_for_status()
    logger.info(f"App {app.id} removed from node {store.node.id}")
