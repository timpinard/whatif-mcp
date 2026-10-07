from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from whatif_mcp.core.model import Account, AccountKind, Model


async def show_model(client: Client) -> dict[str, Any]:
    result = await client.call_tool("show_model", {})
    assert not result.is_error
    assert result.structured_content is not None
    return result.structured_content


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC11_show_model_contents(client: Client, model_w_file: Path) -> None:
    shown = await show_model(client)

    assert shown["today"] == "2026-10-06"
    assert shown["accounts"] == [
        {
            "name": "Checking",
            "kind": "asset",
            "balance": 5000.00,
            "growth_rate": 0.0,
            "volatility": 0.0,
            "balance_as_of": "2026-10-06",
        },
        {
            "name": "Savings",
            "kind": "asset",
            "balance": 0.00,
            "growth_rate": 0.0,
            "volatility": 0.0,
            "balance_as_of": "2026-10-06",
        },
        {
            "name": "Car loan",
            "kind": "liability",
            "balance": 10000.00,
            "growth_rate": 0.06,
            "volatility": 0.0,
            "balance_as_of": "2026-10-06",
        },
    ]
    assert shown["flows"] == [
        {
            "name": "Salary",
            "from": None,
            "to": "Checking",
            "amount": 4000.00,
            "rate": None,
            "rate_of": None,
            "frequency": "monthly",
            "start_date": "2026-11-01",
            "end_date": None,
        },
        {
            "name": "Car payment",
            "from": "Checking",
            "to": "Car loan",
            "amount": 500.00,
            "rate": None,
            "rate_of": None,
            "frequency": "monthly",
            "start_date": "2026-11-01",
            "end_date": None,
        },
    ]
    assert shown["inflation_rate"] == 0.03
    assert shown["net_worth_today"] == -5000.00  # 5000 + 0 - 10000
    assert shown["model_path"] == str(model_w_file)


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC26_money_rounds_half_up_to_cents(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    write_model_file(Model(accounts=(Account("Checking", AccountKind.ASSET, 0.125, today),)))

    shown = await show_model(client)

    assert shown["accounts"][0]["balance"] == 0.13  # half-even would give 0.12
    assert shown["net_worth_today"] == 0.13
