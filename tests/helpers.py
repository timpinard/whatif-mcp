from typing import Any

from mcp import Client
from mcp.types import CallToolResult, TextContent


async def succeed(client: Client, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, error_text(result)
    assert result.structured_content is not None
    return result.structured_content


async def fail(client: Client, tool: str, arguments: dict[str, Any]) -> str:
    result = await client.call_tool(tool, arguments)
    assert result.is_error, result.structured_content
    return error_text(result)


def error_text(result: CallToolResult) -> str:
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


async def what_if(client: Client, changes: list[dict[str, Any]], **options: Any) -> dict[str, Any]:
    return await succeed(client, "what_if", {"changes": changes, **options})
