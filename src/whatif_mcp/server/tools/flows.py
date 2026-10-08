from typing import Any

from mcp import types

from whatif_mcp.core.model import Frequency
from whatif_mcp.server.operations import flows as operations
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import shape_flow, shape_flow_changes
from whatif_mcp.server.tools.writing import write_model_file
from whatif_mcp.store import load_model, resolve_model_path

SET_FLOW_DESCRIPTION = (
    "Create a flow, or update only the given fields of an existing one (names match ignoring "
    "case and surrounding spaces). A flow moves a fixed amount, or a rate of the rate_of "
    "account's balance per year, from one account to another; an omitted from or to is outside "
    "the model. frequency is required for a new flow; start_date defaults to today. JSON null "
    "clears from, to or end_date. Rates are decimals: 0.04 means 4%."
)
REMOVE_FLOW_DESCRIPTION = "Remove a flow (names match ignoring case and surrounding spaces)."

NAME_PROPERTY = {"type": "string", "description": "Flow name."}
DATE_DESCRIPTION = "YYYY-MM-DD"

SET_FLOW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": NAME_PROPERTY,
        "from": {"type": ["string", "null"], "description": "Account paid from; omit for outside."},
        "to": {"type": ["string", "null"], "description": "Account paid to; omit for outside."},
        "amount": {"type": "number", "description": "Fixed amount moved each time, above 0."},
        "rate": {
            "type": "number",
            "description": "Annual rate of rate_of's balance, above 0, at most 1.",
        },
        "rate_of": {"type": "string", "description": "Account whose balance the rate applies to."},
        "frequency": {"type": "string", "enum": [frequency.value for frequency in Frequency]},
        "start_date": {"type": "string", "description": DATE_DESCRIPTION},
        "end_date": {"type": ["string", "null"], "description": DATE_DESCRIPTION},
        "new_name": {"type": "string", "description": "Rename the flow."},
    },
    "required": ["name"],
    "additionalProperties": False,
}

REMOVE_FLOW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"name": NAME_PROPERTY},
    "required": ["name"],
    "additionalProperties": False,
}


def set_flow(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    edit = operations.set_flow(load_model(path), call.arguments, call.today)
    result: dict[str, Any] = {"created": edit.previous is None, "flow": shape_flow(edit.flow)}
    if edit.previous is not None:
        result["previous"] = shape_flow_changes(edit.previous, edit.flow)
    result["similar_flows"] = list(edit.similar_flows)
    write_model_file(path, edit.model)
    return result


def remove_flow(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    removal = operations.remove_flow(load_model(path), call.arguments)
    result = {"removed": shape_flow(removal.flow)}
    write_model_file(path, removal.model)
    return result


TOOLS = (
    RegisteredTool(
        types.Tool(name="set_flow", description=SET_FLOW_DESCRIPTION, input_schema=SET_FLOW_SCHEMA),
        set_flow,
    ),
    RegisteredTool(
        types.Tool(
            name="remove_flow",
            description=REMOVE_FLOW_DESCRIPTION,
            input_schema=REMOVE_FLOW_SCHEMA,
        ),
        remove_flow,
    ),
)
