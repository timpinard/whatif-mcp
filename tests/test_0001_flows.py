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
async def test_AC8_set_flow_creates_updates_and_renames(client: Client, model_w_file: Path) -> None:
    gym = await succeed(
        client,
        "set_flow",
        {"name": "Gym", "from": "Checking", "amount": 50, "frequency": "monthly"},
    )

    assert gym["created"] is True
    assert "previous" not in gym
    assert gym["similar_flows"] == []
    assert flow_named(await shown_flows(client), "Gym") == {
        "name": "Gym",
        "from": "Checking",
        "to": None,
        "amount": 50.00,
        "rate": None,
        "rate_of": None,
        "frequency": "monthly",
        "start_date": "2026-10-06",
        "end_date": None,
    }

    extra = await succeed(
        client,
        "set_flow",
        {
            "name": "Extra car payment",
            "from": "Checking",
            "to": "Car loan",
            "amount": 100,
            "frequency": "monthly",
            "start_date": "2026-11-01",
        },
    )

    assert extra["similar_flows"] == ["Car payment"]

    await succeed(client, "set_flow", {"name": "Car payment", "end_date": "2027-12-01"})
    corrected = await succeed(
        client, "set_flow", {"name": "car payment", "amount": 700, "end_date": None}
    )

    assert corrected["created"] is False
    assert corrected["previous"]["amount"] == 500.00
    assert corrected["similar_flows"] == ["Extra car payment"]
    assert flow_named(await shown_flows(client), "Car payment") == {
        "name": "Car payment",
        "from": "Checking",
        "to": "Car loan",
        "amount": 700.00,
        "rate": None,
        "rate_of": None,
        "frequency": "monthly",
        "start_date": "2026-11-01",
        "end_date": None,
    }

    await succeed(
        client,
        "set_flow",
        {
            "name": "Sweep",
            "from": "Checking",
            "to": "Savings",
            "rate": 0.12,
            "rate_of": "Checking",
            "frequency": "monthly",
        },
    )
    fixed = await succeed(client, "set_flow", {"name": "Sweep", "amount": 50})

    assert (fixed["flow"]["amount"], fixed["flow"]["rate"], fixed["flow"]["rate_of"]) == (
        50.00,
        None,
        None,
    )
    sweep = flow_named(await shown_flows(client), "Sweep")
    assert (sweep["amount"], sweep["rate"], sweep["rate_of"]) == (50.00, None, None)

    await succeed(client, "set_flow", {"name": "Gym", "new_name": "Fitness"})

    assert [flow["name"] for flow in await shown_flows(client)] == [
        "Salary",
        "Car payment",
        "Fitness",
        "Extra car payment",
        "Sweep",
    ]

    file_bytes = model_w_file.read_bytes()
    message = await fail(client, "set_flow", {"name": "Fitness", "new_name": "salary"})

    assert message.split()[0].rstrip(":") == "new_name"
    assert '"Salary"' in message
    assert model_w_file.read_bytes() == file_bytes


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
