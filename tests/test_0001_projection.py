from datetime import date

import pytest

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model
from whatif_mcp.core.projection import Granularity, Projection, horizon_end_date, project

CENT = 0.005


def cents(expected: float) -> object:
    return pytest.approx(expected, abs=CENT)


def asset(name: str, balance: float, growth_rate: float = 0.0) -> Account:
    return Account(name, AccountKind.ASSET, balance, date(2026, 10, 6), growth_rate=growth_rate)


def liability(name: str, balance: float, growth_rate: float = 0.0) -> Account:
    return Account(name, AccountKind.LIABILITY, balance, date(2026, 10, 6), growth_rate=growth_rate)


def fixed_flow(
    name: str,
    amount: float,
    frequency: Frequency,
    start: date,
    *,
    source: str | None = None,
    target: str | None = None,
    end: date | None = None,
) -> Flow:
    return Flow(name, source, target, amount, None, None, frequency, start, end)


def rate_flow(
    name: str,
    rate: float,
    rate_of: str,
    frequency: Frequency,
    start: date,
    *,
    source: str | None = None,
    target: str | None = None,
) -> Flow:
    return Flow(name, source, target, None, rate, rate_of, frequency, start)


def project_years(
    model: Model, today: date, years: int, granularity: Granularity = Granularity.ANNUAL
) -> Projection:
    return project(model, today, horizon_end_date(today, years), granularity)


def balance_at(projection: Projection, label: str, account: str) -> float:
    rows = {row.label: row for row in projection.periods}
    return rows[label].balances[account]


def flow_totals(projection: Projection) -> dict[str, float]:
    return {total.name: total.total for total in projection.flows}


def test_AC14_occurrences_that_take_effect(today: date) -> None:
    model = Model(
        accounts=(asset("Checking", 1000),),
        flows=(
            fixed_flow(
                "Rent",
                100,
                Frequency.MONTHLY,
                date(2026, 1, 15),
                source="Checking",
                end=date(2026, 12, 15),
            ),
            fixed_flow("Tip", 10, Frequency.MONTHLY, today, target="Checking"),
            fixed_flow("Kitchen", 1000, Frequency.ONE_TIME, date(2027, 4, 1), source="Checking"),
            fixed_flow("Bonus", 100, Frequency.ANNUAL, date(2027, 10, 7), target="Checking"),
        ),
    )

    projection = project_years(model, today, 1, Granularity.MONTHLY)

    assert balance_at(projection, "2026-10", "Checking") == cents(900.00)
    assert balance_at(projection, "2026-11", "Checking") == cents(810.00)
    assert balance_at(projection, "2026-12", "Checking") == cents(720.00)
    assert balance_at(projection, "2027-03", "Checking") == cents(750.00)
    assert balance_at(projection, "2027-04", "Checking") == cents(-240.00)
    last_row = projection.periods[-1]
    assert last_row.end_date == date(2027, 10, 6)
    assert last_row.balances["Checking"] == cents(-180.00)
    assert flow_totals(projection) == {
        "Rent": cents(300.00),
        "Tip": cents(120.00),
        "Kitchen": cents(1000.00),
        "Bonus": cents(0.00),
    }
