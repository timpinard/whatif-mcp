from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent

from whatif_mcp.core.model import Account, AccountKind, Model


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


async def shown_accounts(client: Client) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = (await succeed(client, "show_model", {}))["accounts"]
    return accounts


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC4_set_account_creates_with_defaults_and_updates_given_fields(
    client: Client, write_model_file: Callable[[Model], Path]
) -> None:
    created = await succeed(
        client, "set_account", {"name": "Checking", "kind": "asset", "balance": 5000}
    )

    assert created["created"] is True
    assert "previous" not in created
    assert await shown_accounts(client) == [
        {
            "name": "Checking",
            "kind": "asset",
            "balance": 5000.00,
            "growth_rate": 0,
            "volatility": 0,
            "balance_as_of": "2026-10-06",
        }
    ]

    write_model_file(
        Model(accounts=(Account("Checking", AccountKind.ASSET, 5000.0, date(2026, 9, 1)),))
    )

    updated = await succeed(client, "set_account", {"name": " checking", "growth_rate": 0.01})

    assert updated["created"] is False
    assert updated["previous"] == {"growth_rate": 0}
    assert updated["account"]["name"] == "Checking"
    assert await shown_accounts(client) == [
        {
            "name": "Checking",
            "kind": "asset",
            "balance": 5000.00,
            "growth_rate": 0.01,
            "volatility": 0,
            "balance_as_of": "2026-09-01",
        }
    ]

    await succeed(client, "set_account", {"name": "Checking", "balance": 6000})

    assert (await shown_accounts(client))[0]["balance_as_of"] == "2026-10-06"


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC5_rename_account_keeps_flows_and_rejects_collision(
    client: Client, model_w_file: Path
) -> None:
    await succeed(client, "set_account", {"name": "Car loan", "new_name": "Auto loan"})

    flows = (await succeed(client, "show_model", {}))["flows"]
    assert [flow["to"] for flow in flows if flow["name"] == "Car payment"] == ["Auto loan"]

    file_bytes = model_w_file.read_bytes()
    message = await fail(client, "set_account", {"name": "Savings", "new_name": "checking"})

    assert '"Checking"' in message
    assert "new_name" in message
    assert model_w_file.read_bytes() == file_bytes

    await succeed(client, "set_account", {"name": "checking", "new_name": "CHECKING"})

    assert [account["name"] for account in await shown_accounts(client)] == [
        "CHECKING",
        "Savings",
        "Auto loan",
    ]
