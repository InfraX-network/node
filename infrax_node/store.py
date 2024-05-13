from pydantic import BaseModel

from .node import get_app_directory
from .types import Job, Node, NodeState


class Store(BaseModel):
    node: Node | None = None
    state: NodeState = NodeState.IDLE
    job: Job | None = None

    @property
    def app_ids(self) -> set[str]:
        app_dir = get_app_directory()
        return {d.name for d in app_dir.iterdir() if d.is_dir()}


store = Store()
