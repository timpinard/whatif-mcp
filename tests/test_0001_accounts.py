import os
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from conftest import fail, succeed
from mcp import Client

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model


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


NEW_ASSET = {"name": "X", "kind": "asset", "balance": 1}


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize(
    ("arguments", "argument_at_fault", "also_contains"),
    [
        (
            {"name": "Chekcing", "balance": 6000},
            "name",
            ["Checking, Savings, Car loan", "kind and balance", "create"],
        ),
        ({"name": "X", "kind": "asset"}, "balance", []),
        ({"name": "X", "kind": "loan", "balance": 1}, "kind", ["asset, liability"]),
        ({"name": "  ", "kind": "asset", "balance": 1}, "name", []),
        ({"name": "X", "kind": "liability", "balance": -1}, "balance", []),
        ({"name": "X", "kind": "asset", "balance": "lots"}, "balance", []),
        ({**NEW_ASSET, "growth_rate": 7}, "growth_rate", ["decimal", "0.07"]),
        ({**NEW_ASSET, "growth_rate": -1}, "growth_rate", []),
        ({**NEW_ASSET, "growth_rate": 1.5}, "growth_rate", []),
        ({**NEW_ASSET, "volatility": -0.1}, "volatility", []),
        ({**NEW_ASSET, "volatility": 1.5}, "volatility", []),
    ],
)
async def test_AC6_set_account_validation(
    client: Client,
    model_w_file: Path,
    arguments: dict[str, Any],
    argument_at_fault: str,
    also_contains: list[str],
) -> None:
    file_bytes = model_w_file.read_bytes()

    message = await fail(client, "set_account", arguments)

    assert message.split()[0].rstrip(":") == argument_at_fault
    for expected in also_contains:
        assert expected in message
    assert model_w_file.read_bytes() == file_bytes


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC6_set_account_allows_rate_bounds(client: Client, model_w_file: Path) -> None:
    created = await succeed(client, "set_account", {**NEW_ASSET, "growth_rate": 1, "volatility": 1})
    updated = await succeed(
        client, "set_account", {"name": "X", "growth_rate": -0.99, "volatility": 0}
    )

    assert (created["account"]["growth_rate"], created["account"]["volatility"]) == (1, 1)
    assert (updated["account"]["growth_rate"], updated["account"]["volatility"]) == (-0.99, 0)


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC7_remove_account_refused_while_referenced(
    client: Client, write_model_file: Callable[[Model], Path], model_w: Model, today: date
) -> None:
    dividend = Flow(
        "Dividend", None, "Checking", None, 0.02, "Brokerage", Frequency.QUARTERLY, today
    )
    write_model_file(
        replace(
            model_w,
            accounts=(
                *model_w.accounts,
                Account("Old", AccountKind.ASSET, 0.0, today),
                Account("Brokerage", AccountKind.ASSET, 1000.0, today),
            ),
            flows=(*model_w.flows, dividend),
        )
    )

    removed = await succeed(client, "remove_account", {"name": "old"})

    assert removed["removed"]["name"] == "Old"
    assert "Car payment" in await fail(client, "remove_account", {"name": "Car loan"})
    assert "Dividend" in await fail(client, "remove_account", {"name": "Brokerage"})
    assert [account["name"] for account in await shown_accounts(client)] == [
        "Checking",
        "Savings",
        "Car loan",
        "Brokerage",
    ]


@pytest.mark.anyio
@pytest.mark.integration
async def test_R2_kind_change_validates_the_resulting_account(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    path = write_model_file(
        Model(accounts=(Account("Overdrawn", AccountKind.ASSET, -50.0, today),))
    )
    file_bytes = path.read_bytes()

    message = await fail(client, "set_account", {"name": "Overdrawn", "kind": "liability"})

    assert "balance" in message
    assert path.read_bytes() == file_bytes

    changed = await succeed(
        client, "set_account", {"name": "Overdrawn", "kind": "liability", "balance": 50}
    )

    assert changed["previous"] == {"kind": "asset", "balance": -50.00}
    assert changed["account"]["kind"] == "liability"


@pytest.mark.anyio
@pytest.mark.integration
async def test_R16_boolean_is_not_a_number(client: Client, model_w_file: Path) -> None:
    file_bytes = model_w_file.read_bytes()

    message = await fail(client, "set_account", {"name": "X", "kind": "asset", "balance": True})

    assert "balance" in message
    assert model_w_file.read_bytes() == file_bytes


@pytest.mark.anyio
@pytest.mark.integration
async def test_R1_failed_write_is_a_tool_error_naming_the_path(
    client: Client, model_w_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_bytes = model_w_file.read_bytes()

    def failing_replace(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
        raise OSError("simulated failure at the final replace")

    monkeypatch.setattr(os, "replace", failing_replace)

    message = await fail(client, "set_account", {"name": "Checking", "balance": 1})

    assert str(model_w_file) in message
    assert model_w_file.read_bytes() == file_bytes


@pytest.mark.anyio
@pytest.mark.integration
async def test_R16_unknown_argument_is_an_error_listing_valid_ones(
    client: Client, model_w_file: Path
) -> None:
    file_bytes = model_w_file.read_bytes()

    message = await fail(client, "set_account", {"name": "Checking", "balnce": 6000})

    assert message.split()[0] == "balnce"
    assert "name, kind, balance, growth_rate, volatility, new_name" in message
    assert model_w_file.read_bytes() == file_bytes
    assert "none" in await fail(client, "show_model", {"verbose": True})


@pytest.mark.anyio
@pytest.mark.integration
async def test_R2_previous_shows_a_change_below_half_a_cent(
    client: Client, model_w_file: Path
) -> None:
    updated = await succeed(client, "set_account", {"name": "Checking", "balance": 5000.004})

    assert updated["previous"] == {"balance": 5000.00}
