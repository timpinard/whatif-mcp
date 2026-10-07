from pathlib import Path
from typing import Any

import pytest
from helpers import fail, succeed
from mcp import Client


async def shown_flows(client: Client) -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = (await succeed(client, "show_model", {}))["flows"]
    return flows


def flow_named(flows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(flow for flow in flows if flow["name"] == name)


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC10_remove_flow_and_exact_case_insensitive_names(
    client: Client, model_w_file: Path
) -> None:
    file_bytes = model_w_file.read_bytes()

    message = await fail(client, "remove_flow", {"name": "Sal"})

    assert message.split()[0].rstrip(":") == "name"
    assert "Salary, Car payment" in message
    assert model_w_file.read_bytes() == file_bytes

    removed = await succeed(client, "remove_flow", {"name": "  car PAYMENT "})

    assert removed["removed"]["name"] == "Car payment"
    assert [flow["name"] for flow in await shown_flows(client)] == ["Salary"]

    message = await fail(client, "remove_flow", {"name": "Car payment"})

    assert "Salary" in message
    assert "Car payment" not in message.split("names:")[1]
