from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from helpers import fail, succeed, what_if
from mcp import Client

from whatif_mcp.core.model import Account, AccountKind, Model


def by_name(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["name"]: entry for entry in entries}


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC1_transfer_between_own_accounts_moves_no_net_worth(
    client: Client, model_w_file: Path
) -> None:
    extra_saving = {
        "op": "set_flow",
        "name": "Extra saving",
        "from": "Checking",
        "to": "Savings",
        "amount": 300,
        "frequency": "monthly",
        "start_date": "2026-11-01",
    }

    result = await what_if(client, [extra_saving], horizon_years=1)

    assert [row["difference"] for row in result["net_worth"]] == [0.0, 0.0]
    assert result["end_difference"] == 0.0
    accounts = by_name(result["accounts"])
    # 12 occurrences x 300 = 3600
    assert accounts["Savings"]["end_difference"] == 3600.0
    assert accounts["Checking"]["end_difference"] == -3600.0


PAY_CUT = {"op": "set_flow", "name": "Salary", "amount": 3600}


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC2_pay_cut_and_applied_description(client: Client, model_w_file: Path) -> None:
    result = await what_if(client, [PAY_CUT], horizon_years=1)

    # 12 occurrences x -400
    assert result["end_difference"] == -4800.0
    [description] = result["applied"]
    for part in ("set_flow", "Salary", "4000.00", "3600.00"):
        assert part in description
    assert result["flows"] == [
        {
            "name": "Salary",
            "baseline_total": 48000.0,
            "hypothetical_total": 43200.0,
            "difference": -4800.0,
        }
    ]


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC3_one_time_purchase_shows_when_difference_appears(
    client: Client, model_w_file: Path
) -> None:
    kitchen = {
        "op": "set_flow",
        "name": "Kitchen",
        "from": "Checking",
        "amount": 40000,
        "frequency": "one_time",
        "start_date": "2027-04-01",
    }

    result = await what_if(client, [kitchen], horizon_years=1, granularity="monthly")

    differences = {row["period"]: row["difference"] for row in result["net_worth"]}
    # the 40000 leaves Checking on 2027-04-01 and stays out to the horizon
    assert differences == {
        "2026-10": 0.0,
        "2026-11": 0.0,
        "2026-12": 0.0,
        "2027-01": 0.0,
        "2027-02": 0.0,
        "2027-03": 0.0,
        "2027-04": -40000.0,
        "2027-05": -40000.0,
        "2027-06": -40000.0,
        "2027-07": -40000.0,
        "2027-08": -40000.0,
        "2027-09": -40000.0,
        "2027-10": -40000.0,
    }
    assert result["end_difference"] == -40000.0


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC4_paying_loan_faster_shows_payoff_and_interest_saved(
    client: Client, model_w_file: Path
) -> None:
    faster = {"op": "set_flow", "name": "Car payment", "amount": 1000}

    result = await what_if(client, [faster], horizon_years=3)

    car_loan = by_name(result["accounts"])["Car loan"]
    assert car_loan["baseline"]["reaches_zero"] == "2028-08-01"
    assert car_loan["hypothetical"]["reaches_zero"] == "2027-09-01"
    # interest at 0.06 / 12 a month on the balance owed, until each payoff date
    assert car_loan["baseline"]["growth_total"] == 562.51
    assert car_loan["hypothetical"]["growth_total"] == 284.79
    # 284.792 - 562.506, from unrounded values
    assert car_loan["growth_difference"] == -277.71
    assert result["end_difference"] == 277.71
    car_payment = by_name(result["flows"])["Car payment"]
    # payments stop at payoff: 10000 owed + interest (562.51 and 284.79)
    assert car_payment["baseline_total"] == 10562.51
    assert car_payment["hypothetical_total"] == 10284.79


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC5_every_op_applies_in_order_and_combines(
    client: Client, model_w_file: Path
) -> None:
    changes = [
        {
            "op": "set_flow",
            "name": "Gym",
            "from": "Checking",
            "amount": 50,
            "frequency": "monthly",
            "start_date": "2026-11-01",
        },
        {"op": "set_flow", "name": "Gym", "amount": 80},
        {"op": "remove_flow", "name": "Car payment"},
        {"op": "set_account", "name": "Car loan", "growth_rate": 0.03},
        {"op": "set_account", "name": "New loan", "kind": "liability", "balance": 0},
        {
            "op": "set_flow",
            "name": "Borrow",
            "from": "New loan",
            "to": "Checking",
            "amount": 1000,
            "frequency": "one_time",
            "start_date": "2027-01-01",
        },
    ]

    result = await what_if(client, changes, horizon_years=1)

    applied = result["applied"]
    expected_order = [
        ("set_flow", "Gym", "created"),
        ("set_flow", "Gym", "80.00"),
        ("remove_flow", "Car payment"),
        ("set_account", "Car loan", "0.03"),
        ("set_account", "New loan", "created"),
        ("set_flow", "Borrow", "created"),
    ]
    assert len(applied) == len(expected_order)
    for description, parts in zip(applied, expected_order, strict=True):
        for part in parts:
            assert part in description
    assert [flow["name"] for flow in result["flows"]] == ["Car payment", "Gym", "Borrow"]
    flows = by_name(result["flows"])
    # 12 occurrences x 80
    assert flows["Gym"]["hypothetical_total"] == 960.0
    assert flows["Gym"]["baseline_total"] == 0.0
    # 12 occurrences x 500 in the baseline
    assert flows["Car payment"]["baseline_total"] == 6000.0
    assert flows["Car payment"]["hypothetical_total"] == 0.0
    assert flows["Borrow"]["baseline_total"] == 0.0
    accounts = by_name(result["accounts"])
    assert accounts["New loan"]["hypothetical"]["end_balance"] == 1000.0
    # 10000 x 1.0025^12, no payments
    assert accounts["Car loan"]["hypothetical"]["end_balance"] == 10304.16
    assert accounts["New loan"]["baseline"] is None
    # 5000 + 12 x (4000 - 500)
    assert accounts["Checking"]["baseline"] == {
        "kind": "asset",
        "end_balance": 47000.0,
        "reaches_zero": None,
        "growth_total": 0.0,
    }
    assert accounts["Savings"]["baseline"] == {
        "kind": "asset",
        "end_balance": 0.0,
        "reaches_zero": None,
        "growth_total": 0.0,
    }
    # 10000 + 449.00 interest - 12 x 500 (Spec 0002 AC11 baseline)
    assert accounts["Car loan"]["baseline"] == {
        "kind": "liability",
        "end_balance": 4449.0,
        "reaches_zero": None,
        "growth_total": 449.0,
    }
    # 47000 - 4449.00
    assert result["net_worth"][-1]["baseline"] == 42551.0


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC6_one_sided_accounts_and_flows(client: Client, model_w_file: Path) -> None:
    changes = [
        {"op": "remove_flow", "name": "Salary"},
        {
            "op": "set_flow",
            "name": "Side job",
            "to": "Checking",
            "amount": 500,
            "frequency": "monthly",
            "start_date": "2026-11-01",
        },
        {"op": "set_account", "name": "New fund", "kind": "asset", "balance": 1000},
    ]

    result = await what_if(client, changes, horizon_years=1)

    flows = by_name(result["flows"])
    assert set(flows) == {"Salary", "Side job"}
    assert flows["Salary"]["baseline_total"] == 48000.0
    assert flows["Salary"]["hypothetical_total"] == 0.0
    assert flows["Side job"]["baseline_total"] == 0.0
    # 12 occurrences x 500
    assert flows["Side job"]["hypothetical_total"] == 6000.0
    new_fund = by_name(result["accounts"])["New fund"]
    assert new_fund["baseline"] is None
    assert new_fund["hypothetical"]["end_balance"] == 1000.0
    # 1000.00 - 0, the missing baseline side counted as 0
    assert new_fund["end_difference"] == 1000.0
    # no growth rate on either side
    assert new_fund["growth_difference"] == 0.0


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC10_projection_options_match_project(client: Client, model_w_file: Path) -> None:
    todays_money = await what_if(client, [PAY_CUT], horizon_years=1, in_todays_money=True)

    # -4800 / 1.03^(365/365.25)
    assert todays_money["end_difference"] == -4660.29
    assert todays_money["values"] == "todays_money"
    assert todays_money["inflation_rate"] == 0.03

    defaults = await what_if(client, [PAY_CUT])

    assert defaults["horizon"]["years"] == 5
    assert defaults["granularity"] == "annual"
    assert len(defaults["net_worth"]) == 6
    assert defaults["values"] == "nominal"
    assert "inflation_rate" not in defaults

    too_long = {"granularity": "monthly", "horizon_years": 11}
    project_error = await fail(client, "project", too_long)
    what_if_error = await fail(client, "what_if", {"changes": [PAY_CUT], **too_long})

    assert what_if_error == project_error


@pytest.mark.anyio
@pytest.mark.integration
async def test_R2_difference_beyond_the_money_limit_is_refused_as_project_does(
    client: Client, write_model_file: Callable[[Model], Path], today: date
) -> None:
    loan = Account("Loan", AccountKind.LIABILITY, 4e11, today, growth_rate=1.0)
    write_model_file(Model(accounts=(loan,)))
    # 9 years: 4e11 x (1 + 1/12)^108, about 2.27e15, over the 1e15 limit
    project_error = await fail(client, "project", {"horizon_years": 9})
    # 8 years: 4e11 x (1 + 1/12)^96, about 8.69e14 owed, under the limit
    await succeed(client, "project", {"horizon_years": 8})
    as_asset = {"op": "set_account", "name": "Loan", "kind": "asset", "balance": 1e12}

    # hypothetical 1e12 x 2^8 = 2.56e14; difference 2.56e14 + 8.69e14, about 1.13e15
    what_if_error = await fail(client, "what_if", {"changes": [as_asset], "horizon_years": 8})

    assert what_if_error == project_error


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC12_sub_cent_changes_are_named_in_applied(
    client: Client, model_w_file: Path
) -> None:
    sub_cent_raise = {"op": "set_flow", "name": "Salary", "amount": 4000.004}

    result = await what_if(client, [sub_cent_raise], horizon_years=1)

    [description] = result["applied"]
    for part in ("set_flow", "Salary", "amount", "4000.004"):
        assert part in description
    assert "no change" not in description
    [salary] = result["flows"]
    # 12 x 0.004 = 0.048
    assert salary["name"] == "Salary"
    assert salary["difference"] == 0.05

    sub_cent_balance = {"op": "set_account", "name": "Checking", "balance": 5000.004}

    result = await what_if(client, [sub_cent_balance], horizon_years=1)

    [description] = result["applied"]
    for part in ("set_account", "Checking", "balance", "5000.004"):
        assert part in description


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC15_account_blocks_state_their_kind(client: Client, model_w_file: Path) -> None:
    changes = [
        {"op": "remove_account", "name": "Savings"},
        {"op": "set_account", "name": "Savings", "kind": "liability", "balance": 100},
    ]

    result = await what_if(client, changes, horizon_years=1)

    [savings] = [account for account in result["accounts"] if account["name"] == "Savings"]
    assert savings["baseline"]["kind"] == "asset"
    assert savings["baseline"]["end_balance"] == 0.0
    assert savings["hypothetical"]["kind"] == "liability"
    assert savings["hypothetical"]["end_balance"] == 100.0
    assert savings["end_difference"] == 100.0
    # an owed 100 replaces an asset of 0
    assert result["end_difference"] == -100.0
