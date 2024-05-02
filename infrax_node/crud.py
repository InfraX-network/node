from datetime import UTC, datetime

import httpx
from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel

from .config import config
from .exceptions import (
    AppFailedToInstallException,
    AppFailedToUninstallException,
    JobAlreadyExistsException,
    NodeNotFoundException,
    NodeRegistrationFailureException,
)
from .store import store
from .types import App, Config, File, Job, JobState, Node, NodeDef, NodeState, Result


class RegisterDTO(BaseModel):
    ip_address: str
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
            json=RegisterDTO(
                ip_address=config.host.ip_address,
                port=config.host.port,
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


def create_job(app: FastAPI, job: Job) -> Job:
    if app.state.job:
        raise JobAlreadyExistsException("Job already exists")
    job.last_modified = int(datetime.now(UTC).timestamp())
    job.state = JobState.WORKING
    job.start_ts = None
    app.state.job = job
    logger.info(f"Job {job.id} created")
    return job


def waiting_job(job: Job) -> None:
    set_job_state(job, JobState.WORKING)


def start_job(job: Job) -> None:
    job.start_ts = int(datetime.now(UTC).timestamp())
    set_job_state(job, JobState.WORKING)


def set_job_finishing(job: Job) -> None:
    set_job_state(job, JobState.FINISHING)


def set_job_finished(job: Job) -> None:
    set_job_state(job, JobState.FINISHED)


def set_job_state(job: Job, state: JobState) -> None:
    job.state = state
    response = httpx.put(f"{config.router_url}/job/{job.id}", json=job.model_dump())
    response.raise_for_status()
    logger.info(f"Job {job.id} state set to {state.name}")


def upload_file(file: File) -> None:
    response = httpx.post(f"{config.router_url}/file", json=file.model_dump())
    response.raise_for_status()
    logger.info(f"File {file.id} uploaded")


def upload_result(result: Result) -> None:
    response = httpx.post(
        f"{config.router_url}/job/{result.job_id}/result", json=result.model_dump()
    )
    response.raise_for_status()
    logger.info(f"Result for job {result.job_id} uploaded")


def report_failed_app_install(app: App, error: AppFailedToInstallException) -> None:
    app_error_report_dto = AppErrorReportDTO(error=str(error), type="INSTALL_ERROR")
    response = httpx.put(
        f"{config.router_url}/app/{app.id}", json=app_error_report_dto.model_dump()
    )
    response.raise_for_status()
    logger.error(f"Failed to install app {app.id}: {error}")


def report_failed_app_uninstall(app: App, error: AppFailedToUninstallException) -> None:
    app_error_report_dto = AppErrorReportDTO(error=str(error), type="UNINSTALL_ERROR")
    response = httpx.put(
        f"{config.router_url}/app/{app.id}", json=app_error_report_dto.model_dump()
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
        f"{config.router_url}/node/state", json=node_state_dto.model_dump()
    )
    response.raise_for_status()


def add_app(app: App) -> None:
    if not store.node:
        raise NodeNotFoundException("Node not found")
    response = httpx.put(f"{config.router_url}/node/{store.node.id}/app/{app.id}")
    response.raise_for_status()
    logger.info(f"App {app.id} added to node {store.node.id}")


def remove_app(app: App) -> None:
    if not store.node:
        raise NodeNotFoundException("Node not found")
    response = httpx.delete(f"{config.router_url}/node/{store.node.id}/app/{app.id}")
    response.raise_for_status()
    logger.info(f"App {app.id} removed from node {store.node.id}")
