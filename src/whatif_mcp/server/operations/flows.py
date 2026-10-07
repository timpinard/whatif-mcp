from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from whatif_mcp.core.model import Flow, Model
from whatif_mcp.server.operations.arguments import required_text
from whatif_mcp.server.operations.names import clean_name, resolve_named


@dataclass(frozen=True)
class FlowRemoval:
    model: Model
    flow: Flow


def remove_flow(model: Model, arguments: Mapping[str, Any]) -> FlowRemoval:
    name = clean_name("name", required_text(arguments, "name"))
    flow = resolve_named("flow", model.flows, name, "name")
    remaining = tuple(other for other in model.flows if other.name != flow.name)
    return FlowRemoval(replace(model, flows=remaining), flow)
