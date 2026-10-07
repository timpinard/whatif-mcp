import math
from dataclasses import replace
from datetime import date

from whatif_mcp.core.projection import Projection

DAYS_PER_YEAR = 365.25


def in_todays_money(projection: Projection, inflation_rate: float) -> Projection:
    def deflate(value: float, on: date) -> float:
        years = max(0, (on - projection.today).days) / DAYS_PER_YEAR
        return value / math.pow(1 + inflation_rate, years)

    horizon_end = projection.horizon_end
    periods = tuple(
        replace(
            row,
            balances={name: deflate(value, row.end_date) for name, value in row.balances.items()},
            net_worth=deflate(row.net_worth, row.end_date),
        )
        for row in projection.periods
    )
    accounts = tuple(
        replace(
            summary,
            start_balance=deflate(summary.start_balance, projection.today),
            end_balance=deflate(summary.end_balance, horizon_end),
            growth_total=deflate(summary.growth_total, horizon_end),
        )
        for summary in projection.accounts
    )
    flows = tuple(
        replace(total, total=deflate(total.total, horizon_end)) for total in projection.flows
    )
    return replace(projection, periods=periods, accounts=accounts, flows=flows)
