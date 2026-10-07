import json
import stat
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from helpers import fail, succeed
from mcp import Client

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model
from whatif_mcp.server import create_server


def period_labels(projection: dict[str, Any]) -> list[str]:
    return [row["period"] for row in projection["periods"]]


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC22_project_defaults(client: Client, model_w_file: Path) -> None:
    projection = await succeed(client, "project", {})

    assert projection["horizon"] == {
        "years": 5,
        "from": "2026",
        "to": "2031",
        "end_date": "2031-10-06",
    }
    assert projection["granularity"] == "annual"
    assert period_labels(projection) == ["2026", "2027", "2028", "2029", "2030", "2031"]


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC22_project_monthly_ten_years_gives_121_rows(
    client: Client, model_w_file: Path
) -> None:
    projection = await succeed(client, "project", {"granularity": "monthly", "horizon_years": 10})

    # 2026-10 to 2036-10: 3 months in 2026, 12 x 9 for 2027-2035, 10 in 2036 = 121
    assert len(projection["periods"]) == 121
    assert projection["horizon"]["years"] == 10


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC22_project_accepts_an_integral_float_horizon(
    client: Client, model_w_file: Path
) -> None:
    projection = await succeed(client, "project", {"horizon_years": 5.0})

    assert projection["horizon"]["years"] == 5
    assert projection["horizon"]["end_date"] == "2031-10-06"


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize(
    ("arguments", "argument_at_fault", "also_contains"),
    [
        ({"horizon_years": 0}, "horizon_years", ["1 to 50"]),
        ({"horizon_years": 51}, "horizon_years", ["1 to 50"]),
        ({"horizon_years": 2.5}, "horizon_years", ["1 to 50"]),
        ({"granularity": "weekly"}, "granularity", ["monthly, quarterly, annual"]),
        (
            {"granularity": "monthly", "horizon_years": 11},
            "granularity",
            ["10 years", "quarterly", "annual"],
        ),
    ],
)
async def test_AC22_project_argument_checks(
    client: Client,
    model_w_file: Path,
    arguments: dict[str, Any],
    argument_at_fault: str,
    also_contains: list[str],
) -> None:
    file_bytes = model_w_file.read_bytes()

    message = await fail(client, "project", arguments)

    assert message.split()[0].rstrip(":") == argument_at_fault
    for expected in also_contains:
        assert expected in message
    assert model_w_file.read_bytes() == file_bytes


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC22_project_on_an_empty_model_names_set_account(client: Client) -> None:
    message = await fail(client, "project", {})

    assert "no accounts" in message
    assert "set_account" in message


def row_balances(projection: dict[str, Any], account: str) -> list[float]:
    return [row["balances"][account] for row in projection["periods"]]


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC23_project_in_todays_money(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    write_model_file(Model(accounts=(Account("Checking", AccountKind.ASSET, 1000.0, today),)))
    one_year = {"horizon_years": 1, "granularity": "annual"}

    todays_money = await succeed(client, "project", {**one_year, "in_todays_money": True})
    nominal = await succeed(client, "project", one_year)

    # 1000 / 1.03^(86/365.25) = 993.06; 1000 / 1.03^(365/365.25) = 970.89
    assert row_balances(todays_money, "Checking") == [993.06, 970.89]
    assert [row["net_worth"] for row in todays_money["periods"]] == [993.06, 970.89]
    assert todays_money["accounts"][0]["start_balance"] == 1000.00
    assert todays_money["accounts"][0]["end_balance"] == 970.89
    assert todays_money["values"] == "todays_money"
    assert todays_money["inflation_rate"] == 0.03
    assert row_balances(nominal, "Checking") == [1000.00, 1000.00]
    assert nominal["values"] == "nominal"
    assert "inflation_rate" not in nominal


async def shown_inflation_rate(client: Client) -> float:
    rate: float = (await succeed(client, "show_model", {}))["inflation_rate"]
    return rate


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC23_set_inflation_rate(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    path = write_model_file(
        Model(accounts=(Account("Checking", AccountKind.ASSET, 1000.0, today),))
    )

    assert await succeed(client, "set_inflation_rate", {"rate": 0.025}) == {
        "inflation_rate": 0.025,
        "previous": 0.03,
    }

    file_bytes = path.read_bytes()
    message = await fail(client, "set_inflation_rate", {"rate": 3})

    assert message.split()[0] == "rate"
    assert "0.03" in message
    assert path.read_bytes() == file_bytes
    assert await shown_inflation_rate(client) == 0.025

    await succeed(client, "set_inflation_rate", {"rate": 0})
    one_year = {"horizon_years": 1, "granularity": "annual"}
    todays_money = await succeed(client, "project", {**one_year, "in_todays_money": True})
    nominal = await succeed(client, "project", one_year)

    assert todays_money["periods"] == nominal["periods"]
    assert todays_money["inflation_rate"] == 0


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize("rate", [-1, 1, "3%"])
async def test_AC23_set_inflation_rate_refuses_out_of_range(
    client: Client, model_w_file: Path, rate: object
) -> None:
    file_bytes = model_w_file.read_bytes()

    message = await fail(client, "set_inflation_rate", {"rate": rate})

    assert message.split()[0] == "rate"
    assert model_w_file.read_bytes() == file_bytes


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC23_set_inflation_rate_allows_just_inside_the_bounds(
    client: Client, model_w_file: Path
) -> None:
    assert (await succeed(client, "set_inflation_rate", {"rate": -0.99}))["inflation_rate"] == -0.99
    assert (await succeed(client, "set_inflation_rate", {"rate": 0.99}))["previous"] == -0.99


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC1_model_file_location_creation_and_read_only_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, today: date
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("WHATIF_MODEL_PATH", raising=False)
    async with Client(create_server(lambda: today)) as client:
        shown = await succeed(client, "show_model", {})

        assert shown["model_path"] == str(home / ".whatif" / "model.json")

        path = tmp_path / "new" / "model.json"
        monkeypatch.setenv("WHATIF_MODEL_PATH", str(path))
        shown = await succeed(client, "show_model", {})

        assert shown["accounts"] == []
        assert shown["flows"] == []
        assert shown["inflation_rate"] == 0.03
        assert shown["net_worth_today"] == 0.00
        assert shown["model_path"] == str(path)
        assert not path.parent.exists()

        await succeed(client, "set_account", {"name": "Checking", "kind": "asset", "balance": 5000})

        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert json.loads(path.read_text())["version"] == 1
        assert not (home / ".whatif").exists()

        file_bytes = path.read_bytes()
        modified = path.stat().st_mtime_ns
        await succeed(client, "show_model", {})
        await succeed(client, "project", {})

        assert path.read_bytes() == file_bytes
        assert path.stat().st_mtime_ns == modified


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC2_unreadable_file_errors_and_is_not_overwritten(
    client: Client, model_path: Path
) -> None:
    model_path.write_text("{not json")
    for tool, arguments in [
        ("show_model", {}),
        ("set_account", {"name": "X", "kind": "asset", "balance": 1}),
    ]:
        message = await fail(client, tool, arguments)

        assert str(model_path) in message
        assert "not valid JSON" in message
        assert model_path.read_text() == "{not json"

    version_2 = json.dumps({"version": 2, "inflation_rate": 0.03, "accounts": [], "flows": []})
    model_path.write_text(version_2)

    message = await fail(client, "project", {})

    assert "version 2" in message
    assert str(model_path) in message
    assert model_path.read_text() == version_2


LATENCY_BUDGET_SECONDS = 1.0
ACCOUNT_COUNT = 25


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC24_thirty_year_projection_under_one_second(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    names = [f"Account {index}" for index in range(ACCOUNT_COUNT)]
    accounts = tuple(
        Account(name, AccountKind.ASSET, 10000.0, today, growth_rate=0.05) for name in names
    )
    flows = tuple(
        Flow(
            f"Flow {index}",
            names[index],
            names[(index + 1) % ACCOUNT_COUNT],
            100.0,
            None,
            None,
            Frequency.MONTHLY,
            date(2026, 11, 1),
        )
        for index in range(ACCOUNT_COUNT)
    )
    write_model_file(Model(accounts=accounts, flows=flows))

    started = time.perf_counter()
    projection = await succeed(client, "project", {"horizon_years": 30, "granularity": "quarterly"})
    elapsed = time.perf_counter() - started

    assert elapsed < LATENCY_BUDGET_SECONDS
    assert projection["horizon"]["end_date"] == "2056-10-06"


@pytest.mark.anyio
@pytest.mark.integration
async def test_R15_flow_totals_deflate_at_the_horizon_end(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    gift = Flow("Gift", None, "Checking", 100.0, None, None, Frequency.ONE_TIME, date(2026, 11, 1))
    write_model_file(
        Model(accounts=(Account("Checking", AccountKind.ASSET, 0.0, today),), flows=(gift,))
    )

    todays_money = await succeed(client, "project", {"horizon_years": 1, "in_todays_money": True})

    # 100 / 1.03^(365/365.25) = 97.09, not 100 / 1.03^(26/365.25) = 99.79 at the gift's date
    assert todays_money["flows"] == [{"name": "Gift", "total": 97.09}]
    assert todays_money["accounts"][0]["end_balance"] == 97.09


@pytest.mark.anyio
@pytest.mark.integration
async def test_R15_growth_total_deflates_at_the_horizon_end(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    write_model_file(
        Model(accounts=(Account("Savings", AccountKind.ASSET, 1000.0, today, growth_rate=0.07),))
    )

    todays_money = await succeed(client, "project", {"horizon_years": 1, "in_todays_money": True})

    # nominal growth 1000 x 0.07 = 70.00 (AC17); 70 / 1.03^(365/365.25) = 67.96
    assert todays_money["accounts"][0]["growth_total"] == 67.96
