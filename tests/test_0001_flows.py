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


MONTHLY_FROM_CHECKING = {"name": "X", "from": "Checking", "frequency": "monthly"}
FIXED_FROM_CHECKING = {**MONTHLY_FROM_CHECKING, "amount": 50}
RATE_FROM_CHECKING = {**MONTHLY_FROM_CHECKING, "rate": 0.1, "rate_of": "Savings"}
ACCOUNT_NAMES = "Checking, Savings, Car loan"


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize(
    ("arguments", "argument_at_fault", "also_contains"),
    [
        ({"name": "X", "amount": 50, "frequency": "monthly"}, "from", ["to"]),
        ({**FIXED_FROM_CHECKING, "to": "checking"}, "to", []),
        ({**FIXED_FROM_CHECKING, "rate": 0.1, "rate_of": "Savings"}, "amount", ["rate"]),
        (MONTHLY_FROM_CHECKING, "amount", ["rate"]),
        ({**MONTHLY_FROM_CHECKING, "rate": 0.1}, "rate_of", []),
        ({**FIXED_FROM_CHECKING, "amount": 0}, "amount", []),
        ({**FIXED_FROM_CHECKING, "amount": "lots"}, "amount", []),
        ({**RATE_FROM_CHECKING, "rate": 0}, "rate", []),
        ({**RATE_FROM_CHECKING, "rate": 1.5}, "rate", ["decimal"]),
        (
            {**FIXED_FROM_CHECKING, "start_date": "2026-11-01", "end_date": "2026-10-31"},
            "end_date",
            ["start_date"],
        ),
        ({**FIXED_FROM_CHECKING, "frequency": "daily"}, "frequency", ["monthly", "one_time"]),
        ({**FIXED_FROM_CHECKING, "start_date": "10/1/2026"}, "start_date", ["YYYY-MM-DD"]),
        (
            {**FIXED_FROM_CHECKING, "frequency": "one_time", "start_date": "2026-10-06"},
            "start_date",
            ["never fire"],
        ),
        ({**FIXED_FROM_CHECKING, "to": "Marina"}, "to", ['"Marina"', ACCOUNT_NAMES]),
        ({**RATE_FROM_CHECKING, "rate_of": "Marina"}, "rate_of", ['"Marina"', ACCOUNT_NAMES]),
    ],
)
async def test_AC9_set_flow_validation(
    client: Client,
    model_w_file: Path,
    arguments: dict[str, Any],
    argument_at_fault: str,
    also_contains: list[str],
) -> None:
    file_bytes = model_w_file.read_bytes()

    message = await fail(client, "set_flow", arguments)

    assert message.split()[0].rstrip(":") == argument_at_fault
    for expected in also_contains:
        assert expected in message
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
