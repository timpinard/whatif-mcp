from dataclasses import fields
from typing import Any

from whatif_mcp.core.model import Account, Flow
from whatif_mcp.core.money import round_money
from whatif_mcp.core.projection import Granularity, Projection
from whatif_mcp.server.operations.projection import (
    DEFAULT_GRANULARITY,
    DEFAULT_HORIZON_YEARS,
    MAX_HORIZON_YEARS,
    MAX_MONTHLY_HORIZON_YEARS,
    MIN_HORIZON_YEARS,
    ProjectArguments,
)

FLOW_RESULT_KEYS = {"from_account": "from", "to_account": "to"}
NOMINAL = "nominal"
TODAYS_MONEY = "todays_money"

PROJECTION_OPTION_PROPERTIES: dict[str, Any] = {
    "horizon_years": {
        "type": "integer",
        "minimum": MIN_HORIZON_YEARS,
        "maximum": MAX_HORIZON_YEARS,
        "description": f"Years ahead, default {DEFAULT_HORIZON_YEARS}.",
    },
    "granularity": {
        "type": "string",
        "enum": [granularity.value for granularity in Granularity],
        "description": f"One row per period, default {DEFAULT_GRANULARITY.value}. "
        f"monthly only up to {MAX_MONTHLY_HORIZON_YEARS} years.",
    },
    "in_todays_money": {
        "type": "boolean",
        "description": "Deflate every value to today's money by the model's inflation rate.",
    },
}


def shape_account(account: Account) -> dict[str, Any]:
    return {
        "name": account.name,
        "kind": account.kind.value,
        "balance": round_money(account.balance),
        "growth_rate": account.growth_rate,
        "volatility": account.volatility,
        "balance_as_of": account.balance_as_of.isoformat(),
    }


def shape_flow(flow: Flow) -> dict[str, Any]:
    return {
        "name": flow.name,
        "from": flow.from_account,
        "to": flow.to_account,
        "amount": None if flow.amount is None else round_money(flow.amount),
        "rate": flow.rate,
        "rate_of": flow.rate_of,
        "frequency": flow.frequency.value,
        "start_date": flow.start_date.isoformat(),
        "end_date": None if flow.end_date is None else flow.end_date.isoformat(),
    }


def shape_flow_changes(previous: Flow, flow: Flow) -> dict[str, Any]:
    earlier = shape_flow(previous)
    changed_keys = (
        FLOW_RESULT_KEYS.get(field.name, field.name)
        for field in fields(Flow)
        if getattr(previous, field.name) != getattr(flow, field.name)
    )
    return {key: earlier[key] for key in changed_keys}


def shape_horizon(projection: Projection, years: int) -> dict[str, Any]:
    return {
        "today": projection.today.isoformat(),
        "horizon": {
            "years": years,
            "from": projection.periods[0].label,
            "to": projection.periods[-1].label,
            "end_date": projection.horizon_end.isoformat(),
        },
        "granularity": projection.granularity.value,
    }


def shape_values(given: ProjectArguments, inflation_rate: float) -> dict[str, Any]:
    if given.is_todays_money:
        return {"values": TODAYS_MONEY, "inflation_rate": inflation_rate}
    return {"values": NOMINAL}
