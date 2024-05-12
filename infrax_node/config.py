from __future__ import annotations

from pathlib import Path

from box import Box

from .types import Config, Host, NodeDef, Spec


def load_config(path: Path) -> Config:
    data = Box.from_toml(filename=path)

    router_url = data.router_url
    compute_node = data.compute_node
    float_types = data.float_types
    host = data.host

    spec = Spec(
        # Assuming RAM and VRAM are provided as "XXGB"
        ram=int(compute_node.ram.replace("GB", "")),
        vram=int(compute_node.vram.replace("GB", "")),
        FP80=float_types.get("FP80", False),
        FP64=float_types.get("FP64", False),
        FP32=float_types.get("FP32", False),
        FP16=float_types.get("FP16", False),
        FP8=float_types.get("FP8", False),
        FP4=float_types.get("FP4", False),
        BF16=float_types.get("BF16", False),
        TF32=float_types.get("TF32", False),
        NF4=float_types.get("NF4", False),
    )

    return Config(
        router_url=router_url,
        host=Host(
            external_port=host.external_port,
            local_only=host.local_only,
            app_dir=host.app_dir,
        ),
        node=NodeDef(
            eth_address=compute_node.eth_address,
            cpu=compute_node.cpu,
            gpu=compute_node.gpu,
            spec=spec,
        ),
    )


config = load_config(Path(__file__).parent.parent / "config.toml")
