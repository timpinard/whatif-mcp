from pathlib import Path
from typing import Any

import pytest
from helpers import what_if
from mcp import Client

SALARY = {
    "name": "Salary",
    "to": "Checking",
    "amount": 4000,
    "frequency": "monthly",
    "start_date": "2026-11-01",
}


def named(entries: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [entry for entry in entries if entry["name"] == name]


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC11_renamed_and_re_added_entries_match_their_baseline(
    client: Client, model_w_file: Path
) -> None:
    renames = [
        {"op": "set_account", "name": "Car loan", "new_name": "Auto loan"},
        {"op": "set_account", "name": "auto loan", "balance": 8000},
        {"op": "set_flow", "name": "Car payment", "new_name": "Loan payment", "amount": 600},
    ]

    result = await what_if(client, renames, horizon_years=1)

    assert named(result["accounts"], "Car loan") == []
    [auto_loan] = named(result["accounts"], "Auto loan")
    # 10000 + 449.00 interest - 12 x 500
    assert auto_loan["baseline"]["end_balance"] == 4449.0
    # 8000 + 292.09 interest - 12 x 600
    assert auto_loan["hypothetical"]["end_balance"] == 1092.09
    assert auto_loan["end_difference"] == -3356.91
    assert auto_loan["baseline"]["growth_total"] == 449.0
    assert auto_loan["hypothetical"]["growth_total"] == 292.09
    assert auto_loan["growth_difference"] == -156.91
    # 12 x 500 and 12 x 600
    assert result["flows"] == [
        {
            "name": "Loan payment",
            "baseline_total": 6000.0,
            "hypothetical_total": 7200.0,
            "difference": 1200.0,
        }
    ]

    re_added = [{"op": "remove_flow", "name": "Salary"}, {"op": "set_flow", **SALARY}]

    result = await what_if(client, re_added, horizon_years=1)

    assert result["flows"] == []
    assert result["end_difference"] == 0.0


@pytest.mark.anyio
@pytest.mark.integration
async def test_R7_rename_onto_a_name_removed_earlier_keeps_both_entries(
    client: Client, model_w_file: Path
) -> None:
    changes = [
        {"op": "remove_flow", "name": "Car payment"},
        {"op": "remove_account", "name": "Car loan"},
        {"op": "set_account", "name": "Savings", "new_name": "Car loan", "balance": 2500},
    ]

    result = await what_if(client, changes, horizon_years=1)

    assert [account["name"] for account in result["accounts"]] == [
        "Checking",
        "Car loan",
        "Car loan",
    ]
    renamed_savings, removed_car_loan = named(result["accounts"], "Car loan")
    assert renamed_savings["baseline"]["end_balance"] == 0.0
    assert renamed_savings["hypothetical"]["end_balance"] == 2500.0
    assert renamed_savings["end_difference"] == 2500.0
    # 10000 + 449.00 interest - 12 x 500
    assert removed_car_loan["baseline"]["end_balance"] == 4449.0
    assert removed_car_loan["hypothetical"] is None
    assert removed_car_loan["end_difference"] == -4449.0


@pytest.mark.anyio
@pytest.mark.integration
async def test_R7_re_creating_a_removed_account_in_another_case_resumes_it(
    client: Client, model_w_file: Path
) -> None:
    changes = [
        {"op": "remove_account", "name": "Savings"},
        {"op": "set_account", "name": "SAVINGS", "kind": "asset", "balance": 1000},
    ]

    result = await what_if(client, changes, horizon_years=1)

    assert [account["name"] for account in result["accounts"]] == [
        "Checking",
        "SAVINGS",
        "Car loan",
    ]
    [savings] = named(result["accounts"], "SAVINGS")
    assert savings["baseline"]["end_balance"] == 0.0
    assert savings["hypothetical"]["end_balance"] == 1000.0
    assert savings["end_difference"] == 1000.0


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC13_re_created_name_resumes_its_baseline_entry_first(
    client: Client, model_w_file: Path
) -> None:
    renamed_away = [
        {"op": "set_flow", "name": "Salary", "new_name": "Pay"},
        {"op": "remove_flow", "name": "Pay"},
        {"op": "set_flow", **SALARY},
    ]

    result = await what_if(client, renamed_away, horizon_years=1)

    assert result["flows"] == []
    assert result["end_difference"] == 0.0

    renamed_onto = [
        {"op": "remove_flow", "name": "Salary"},
        {"op": "set_flow", "name": "Car payment", "new_name": "Salary"},
        {"op": "remove_flow", "name": "Salary"},
        {"op": "set_flow", **SALARY},
    ]

    result = await what_if(client, renamed_onto, horizon_years=1)

    # 12 x 500 in the baseline, none in the hypothetical
    assert result["flows"] == [
        {
            "name": "Car payment",
            "baseline_total": 6000.0,
            "hypothetical_total": 0.0,
            "difference": -6000.0,
        }
    ]
    # 53000.00 (5000 + 12 x 4000) - 10616.78 (10000 x 1.005^12) - baseline net worth 42551.00
    assert result["end_difference"] == -167.78
