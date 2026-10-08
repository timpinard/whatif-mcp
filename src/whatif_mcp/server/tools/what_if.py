from datetime import date
from typing import Any

from mcp import types

from whatif_mcp.core.comparison import AccountComparison, Comparison, compare, difference_values
from whatif_mcp.core.model import Model
from whatif_mcp.core.money import round_money
from whatif_mcp.core.projection import AccountSummary, Projection, horizon_end_date, project
from whatif_mcp.core.todays_money import in_todays_money
from whatif_mcp.server.operations.projection import (
    ProjectArguments,
    check_has_accounts,
    check_reportable,
    check_reportable_values,
    parse_project_arguments,
)
from whatif_mcp.server.operations.what_if import apply_changes
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import shape_horizon
from whatif_mcp.server.tools.project import NOMINAL, PROJECT_SCHEMA, TODAYS_MONEY
from whatif_mcp.store import load_model, resolve_model_path

CHANGES_KEY = "changes"

WHAT_IF_DESCRIPTION = (
    "Compare the model as it is (the baseline) with a copy changed by a list of changes, "
    "projected with the same options as project. Each change is an object with op (set_account, "
    "remove_account, set_flow or remove_flow) and that tool's arguments, applied in order. "
    "Nothing is saved."
)

WHAT_IF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        CHANGES_KEY: {
            "type": "array",
            "items": {"type": "object"},
            "minItems": 1,
            "description": 'Changes in order, e.g. {"op": "set_flow", "name": "Salary", '
            '"amount": 3600}.',
        },
        **PROJECT_SCHEMA["properties"],
    },
    "required": [CHANGES_KEY],
    "additionalProperties": False,
}


def what_if(call: ToolCall) -> dict[str, Any]:
    options = {key: value for key, value in call.arguments.items() if key != CHANGES_KEY}
    given = parse_project_arguments(options)
    model = load_model(resolve_model_path())
    check_has_accounts(model)
    applied = apply_changes(model, call.arguments[CHANGES_KEY], call.today)
    baseline = _projection(model, call.today, given)
    hypothetical = _projection(applied.model, call.today, given)
    values: dict[str, Any] = {"values": NOMINAL}
    if given.is_todays_money:
        values = {"values": TODAYS_MONEY, "inflation_rate": model.inflation_rate}
    comparison = compare(baseline, hypothetical, applied.account_matches, applied.flow_matches)
    check_reportable_values(difference_values(comparison))
    return {
        **shape_horizon(baseline, given.years),
        **values,
        "applied": list(applied.descriptions),
        **_shape_comparison(comparison),
        "persisted": False,
    }


def _projection(model: Model, today: date, given: ProjectArguments) -> Projection:
    projection = project(model, today, horizon_end_date(today, given.years), given.granularity)
    if given.is_todays_money:
        projection = in_todays_money(projection, model.inflation_rate)
    check_reportable(projection)
    return projection


def _shape_comparison(comparison: Comparison) -> dict[str, Any]:
    return {
        "net_worth": [
            {
                "period": row.label,
                "end_date": row.end_date.isoformat(),
                "baseline": round_money(row.baseline),
                "hypothetical": round_money(row.hypothetical),
                "difference": round_money(row.difference),
            }
            for row in comparison.net_worth
        ],
        "end_difference": round_money(comparison.end_difference),
        "accounts": [_shape_account(account) for account in comparison.accounts],
        "flows": [
            {
                "name": flow.name,
                "baseline_total": round_money(flow.baseline_total),
                "hypothetical_total": round_money(flow.hypothetical_total),
                "difference": round_money(flow.difference),
            }
            for flow in comparison.flows
        ],
    }


def _shape_account(account: AccountComparison) -> dict[str, Any]:
    return {
        "name": account.name,
        "baseline": _shape_summary(account.baseline),
        "hypothetical": _shape_summary(account.hypothetical),
        "end_difference": round_money(account.end_difference),
        "growth_difference": round_money(account.growth_difference),
    }


def _shape_summary(summary: AccountSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "end_balance": round_money(summary.end_balance),
        "reaches_zero": None if summary.reaches_zero is None else summary.reaches_zero.isoformat(),
        "growth_total": round_money(summary.growth_total),
    }


TOOLS = (
    RegisteredTool(
        types.Tool(name="what_if", description=WHAT_IF_DESCRIPTION, input_schema=WHAT_IF_SCHEMA),
        what_if,
    ),
)
