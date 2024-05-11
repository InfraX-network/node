from pathlib import Path

from pydantic import BaseModel

from .config import config
from .types import Job, Node, NodeState


class Store(BaseModel):
    node: Node | None = None
    state: NodeState = NodeState.IDLE
    job: Job | None = None

    @property
    def app_ids(self):
        app_dir = Path(config.host.app_dir)
        return [d.name for d in app_dir.iterdir() if d.is_dir()]


store = Store()
