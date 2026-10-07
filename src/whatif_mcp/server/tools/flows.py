from typing import Any

from mcp import types

from whatif_mcp.server.operations import flows as operations
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import shape_flow
from whatif_mcp.server.tools.writing import write_model_file
from whatif_mcp.store import load_model, resolve_model_path

REMOVE_FLOW_DESCRIPTION = "Remove a flow (names match ignoring case and surrounding spaces)."

NAME_PROPERTY = {"type": "string", "description": "Flow name."}

REMOVE_FLOW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"name": NAME_PROPERTY},
    "required": ["name"],
    "additionalProperties": False,
}


def remove_flow(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    removal = operations.remove_flow(load_model(path), call.arguments)
    write_model_file(path, removal.model)
    return {"removed": shape_flow(removal.flow)}


TOOLS = (
    RegisteredTool(
        types.Tool(
            name="remove_flow",
            description=REMOVE_FLOW_DESCRIPTION,
            input_schema=REMOVE_FLOW_SCHEMA,
        ),
        remove_flow,
    ),
)
