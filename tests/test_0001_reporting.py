import math
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from helpers import fail, succeed
from mcp import Client

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model

ONE_YEAR_MONTHLY = {"horizon_years": 1, "granularity": "monthly"}
ZERO_PERIOD_LABELS = tuple(f"2027-{month:02d}" for month in range(1, 11))


def emptied_account(today: date, name: str, balance: float, payment: float) -> Model:
    return Model(
        accounts=(Account(name, AccountKind.ASSET, balance, today),),
        flows=(
            Flow(
                "Spend",
                name,
                None,
                payment,
                None,
                None,
                Frequency.MONTHLY,
                date(2026, 11, 1),
                date(2027, 1, 1),
            ),
        ),
    )


def numbers_in(value: Any) -> Iterator[float]:
    if isinstance(value, dict):
        for item in value.values():
            yield from numbers_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from numbers_in(item)
    elif isinstance(value, float):
        yield value


def balances_by_period(result: dict[str, Any], name: str) -> dict[str, float]:
    return {row["period"]: row["balances"][name] for row in result["periods"]}


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC32_reaches_zero_at_cents_and_no_negative_zero(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    write_model_file(emptied_account(today, "Checking", 30.03, 10.01))

    result = await succeed(client, "project", ONE_YEAR_MONTHLY)

    assert result["accounts"][0]["reaches_zero"] == "2027-01-01"  # 30.03 - 3 x 10.01 = 3.6e-15
    balances = balances_by_period(result, "Checking")
    assert [balances[label] for label in ZERO_PERIOD_LABELS] == [0.0] * 10  # 2027-01 to 2027-10


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC32_no_negative_zero_anywhere_in_the_result(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    write_model_file(emptied_account(today, "Holiday", 0.3, 0.1))

    result = await succeed(client, "project", ONE_YEAR_MONTHLY)

    assert result["accounts"][0]["reaches_zero"] == "2027-01-01"  # 0.3 - 3 x 0.1 = -2.8e-17
    negative_zeros = [
        number for number in numbers_in(result) if number == 0 and math.copysign(1, number) < 0
    ]
    assert negative_zeros == []


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC33_start_date_on_or_after_1900(client: Client, model_w_file: Path) -> None:
    before = model_w_file.read_bytes()
    arguments = {"name": "Old", "to": "Checking", "amount": 1, "frequency": "weekly"}

    message = await fail(client, "set_flow", {**arguments, "start_date": "1899-12-31"})

    assert message.startswith("start_date ")
    assert model_w_file.read_bytes() == before
    result = await succeed(client, "set_flow", {**arguments, "start_date": "1900-01-01"})
    assert result["flow"]["start_date"] == "1900-01-01"


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC34_file_flow_starting_before_1900_does_not_match_the_shape(
    client: Client, write_model_file: Callable[[Model], Path], model_w: Model
) -> None:
    gym = Flow("Gym", "Checking", None, 50.0, None, None, Frequency.MONTHLY, date(1899, 12, 31))
    path = write_model_file(replace(model_w, flows=(*model_w.flows, gym)))
    before = path.read_bytes()

    message = await fail(client, "show_model", {})

    assert str(path) in message
    assert "start_date" in message
    assert path.read_bytes() == before
