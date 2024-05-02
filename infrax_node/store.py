from pydantic import BaseModel

from .types import Job, Node, NodeState
from .util import get_installed_apps


class Store(BaseModel):
    node: Node | None = None
    state: NodeState = NodeState.IDLE
    job: Job | None = None

    @property
    def app_ids(self):
        return get_installed_apps()


store = Store()
