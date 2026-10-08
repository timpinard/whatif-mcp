from dataclasses import fields
from typing import Any

from whatif_mcp.core.model import Account, Flow
from whatif_mcp.core.money import round_money

FLOW_RESULT_KEYS = {"from_account": "from", "to_account": "to"}


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
