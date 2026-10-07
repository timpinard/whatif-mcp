from datetime import date

import pytest

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model
from whatif_mcp.core.projection import (
    AccountSummary,
    Granularity,
    Projection,
    horizon_end_date,
    project,
)

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


def summary_of(projection: Projection, account: str) -> AccountSummary:
    return next(summary for summary in projection.accounts if summary.name == account)


def test_AC16_borrowing_and_payment_capped_at_amount_owed(today: date) -> None:
    model = Model(
        accounts=(asset("Checking", 1000), liability("Loan", 0)),
        flows=(
            fixed_flow(
                "Borrow",
                300,
                Frequency.ONE_TIME,
                date(2026, 11, 1),
                source="Loan",
                target="Checking",
            ),
            fixed_flow(
                "Pay", 500, Frequency.MONTHLY, date(2026, 12, 1), source="Checking", target="Loan"
            ),
        ),
    )

    projection = project_years(model, today, 1, Granularity.MONTHLY)

    november = next(row for row in projection.periods if row.label == "2026-11")
    assert november.balances["Loan"] == cents(300.00)
    assert november.balances["Checking"] == cents(1300.00)
    assert november.net_worth == cents(1000.00)
    later_rows = [row for row in projection.periods if row.end_date >= date(2026, 12, 31)]
    assert len(later_rows) == 11
    for row in later_rows:
        assert row.balances["Loan"] == cents(0.00)
        assert row.balances["Checking"] == cents(1000.00)
    assert flow_totals(projection)["Pay"] == cents(300.00)
    assert summary_of(projection, "Loan").reaches_zero == date(2026, 12, 1)


def test_AC17_asset_growth_is_effective_annual_and_none_at_or_below_zero(today: date) -> None:
    model = Model(
        accounts=(
            asset("Savings", 1000, growth_rate=0.07),
            asset("Overdrawn", -500, growth_rate=0.12),
            asset("Empty", 0, growth_rate=0.12),
        )
    )

    monthly = project_years(model, today, 1, Granularity.MONTHLY)

    assert balance_at(monthly, "2026-10", "Savings") == cents(1000.00)
    assert balance_at(monthly, "2026-11", "Savings") == cents(1005.65)  # 1000 x 1.07^(1/12)
    assert balance_at(monthly, "2026-12", "Savings") == cents(1011.34)  # 1000 x 1.07^(2/12)
    assert monthly.periods[-1].balances["Savings"] == cents(1070.00)  # 1000 x 1.07
    assert summary_of(monthly, "Savings").growth_total == cents(70.00)
    annual = project_years(model, today, 2)
    assert annual.periods[-1].balances["Savings"] == cents(1144.90)  # 1000 x 1.07^2
    for projection in (monthly, annual):
        for row in projection.periods:
            assert row.balances["Overdrawn"] == cents(-500.00)
            assert row.balances["Empty"] == cents(0.00)
        assert summary_of(projection, "Overdrawn").growth_total == cents(0.00)
        assert summary_of(projection, "Empty").growth_total == cents(0.00)


def test_AC18_liability_interest_is_apr_monthly_before_flows(today: date, model_w: Model) -> None:
    projection = project_years(model_w, today, 1, Granularity.MONTHLY)

    assert balance_at(projection, "2026-10", "Car loan") == cents(10000.00)
    assert balance_at(projection, "2026-11", "Car loan") == cents(9550.00)  # 10000 + 50 - 500
    assert balance_at(projection, "2026-12", "Car loan") == cents(9097.75)  # 9550 + 47.75 - 500
    assert projection.periods[-1].balances["Car loan"] == cents(4449.00)
    assert summary_of(projection, "Car loan").growth_total == cents(449.00)

    cards = Model(
        accounts=(liability("Card", 1200, growth_rate=0.12), liability("Paid off", 0, 0.2))
    )
    cards_projection = project_years(cards, today, 1)
    assert summary_of(cards_projection, "Card").end_balance == cents(1352.19)  # 1200 x 1.01^12
    assert summary_of(cards_projection, "Paid off").end_balance == cents(0.00)
    assert summary_of(cards_projection, "Paid off").growth_total == cents(0.00)
