import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from mcp import types
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server

from whatif_mcp.core.errors import WhatIfError

EMPTY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ToolCall:
    arguments: Mapping[str, Any]
    today: date


ToolHandler = Callable[[ToolCall], dict[str, Any]]


@dataclass(frozen=True)
class RegisteredTool:
    definition: types.Tool
    handler: ToolHandler


class UnknownToolError(WhatIfError):
    pass


class UnknownArgumentError(WhatIfError):
    pass


def create_registry_server(
    name: str, tools: Sequence[RegisteredTool], today: Callable[[], date]
) -> Server[Any]:
    tools_by_name = {tool.definition.name: tool for tool in tools}

    async def on_list_tools(
        context: ServerRequestContext[Any], params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[tool.definition for tool in tools])

    async def on_call_tool(
        context: ServerRequestContext[Any], params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        return call_tool(tools_by_name, params.name, ToolCall(params.arguments or {}, today()))

    return Server(name, on_list_tools=on_list_tools, on_call_tool=on_call_tool)


def call_tool(
    tools_by_name: Mapping[str, RegisteredTool], tool_name: str, call: ToolCall
) -> types.CallToolResult:
    try:
        tool = _find_tool(tools_by_name, tool_name)
        check_argument_names(tool.definition, call.arguments)
        result = tool.handler(call)
    except WhatIfError as error:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=str(error))], is_error=True
        )
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(result))],
        structured_content=result,
    )


def _find_tool(tools_by_name: Mapping[str, RegisteredTool], tool_name: str) -> RegisteredTool:
    if tool_name not in tools_by_name:
        raise UnknownToolError(
            f"There is no tool named {tool_name}. Tools: {', '.join(tools_by_name)}."
        )
    return tools_by_name[tool_name]


def check_argument_names(definition: types.Tool, arguments: Mapping[str, Any]) -> None:
    known = list(definition.input_schema.get("properties", {}))
    unknown = [argument for argument in arguments if argument not in known]
    if unknown:
        raise UnknownArgumentError(
            f"{', '.join(unknown)} is not an argument of {definition.name}. "
            f"Arguments: {', '.join(known) or 'none'}."
        )
