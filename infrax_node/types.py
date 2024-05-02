from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Config(BaseModel):
    router_url: str
    host: Host
    node: NodeDef


class Host(BaseModel):
    ip_address: str
    port: int
    local_only: bool = False
    app_dir: str


class NodeDef(BaseModel):
    eth_address: str
    spec: Spec
    cpu: str | None = None
    gpu: str | None = None


class Node(BaseModel):
    id: str
    eth_address: str
    cpu: str | None = None
    gpu: str | None = None
    host: str
    location: str | None = None
    spec_id: str

    job_id: str | None
    state: NodeState

    @property
    def cpu_only(self) -> bool:
        return self.gpu is None


class App(BaseModel):
    id: str
    eth_address: str
    name: str | None
    description: str | None
    meta: dict[str, str] | None = None
    spec_id: str
    ts: int
    last_modified: int
    files: list[File]


class Spec(BaseModel):
    ram: int
    vram: int
    FP80: bool | None = False
    FP64: bool | None = False
    FP32: bool | None = False
    FP16: bool | None = False
    FP8: bool | None = False
    FP4: bool | None = False
    BF16: bool | None = False
    TF32: bool | None = False
    NF4: bool | None = False


class NodeState(str, Enum):
    BUSY = "BUSY"
    IDLE = "IDLE"


class JobState(str, Enum):
    CREATED = "CREATED"
    WORKING = "WORKING"
    FINISHING = "FINISHING"
    FINISHED = "FINISHED"


class Job(BaseModel):
    id: str
    app_id: str
    eth_address: str
    time_to_give_up: int | None = None
    state: JobState
    start_ts: int | None
    ts: int
    last_modified: int
    files: list[File] | None = None


class Result(BaseModel):
    job_id: str
    execution_time: float
    output: str | None = None
    success: bool
    error: str | None = None
    file_ids: list[str] | None = None


class File(BaseModel):
    id: str
    name: str
    path: str | None = None
    content_type: str | None = None
    size: int


class FileObj(BaseModel):
    name: str
    path: str
