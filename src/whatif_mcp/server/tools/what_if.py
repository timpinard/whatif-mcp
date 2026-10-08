from collections.abc import Mapping
from typing import Any

from mcp import types

from whatif_mcp.core.comparison import AccountComparison, Comparison, compare, difference_values
from whatif_mcp.core.money import round_money
from whatif_mcp.core.projection import AccountSummary
from whatif_mcp.server.operations.arguments import ArgumentError
from whatif_mcp.server.operations.projection import (
    EmptyModelError,
    check_has_accounts,
    check_reportable_values,
    parse_project_arguments,
    project_with_options,
)
from whatif_mcp.server.operations.what_if import OPS, apply_changes
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import PROJECTION_OPTION_PROPERTIES, shape_horizon, shape_values
from whatif_mcp.server.tools import accounts, flows
from whatif_mcp.store import load_model, resolve_model_path

CHANGES_KEY = "changes"
OP_DEFINITIONS = {
    tool.definition.name: tool.definition
    for tool in (*accounts.TOOLS, *flows.TOOLS)
    if tool.definition.name in OPS
}

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
        **PROJECTION_OPTION_PROPERTIES,
    },
    "required": [CHANGES_KEY],
    "additionalProperties": False,
}


def what_if(call: ToolCall) -> dict[str, Any]:
    options = {key: value for key, value in call.arguments.items() if key != CHANGES_KEY}
    given = parse_project_arguments(options)
    changes = _changes(call.arguments)
    model = load_model(resolve_model_path())
    check_has_accounts(model)
    applied = apply_changes(model, changes, call.today, OP_DEFINITIONS)
    if not applied.model.accounts:
        raise EmptyModelError(
            "The hypothetical model has no accounts to project: the changes remove every account."
        )
    baseline = project_with_options(model, call.today, given)
    hypothetical = project_with_options(applied.model, call.today, given)
    comparison = compare(baseline, hypothetical, applied.account_matches, applied.flow_matches)
    check_reportable_values(difference_values(comparison))
    return {
        **shape_horizon(baseline, given.years),
        **shape_values(given, model.inflation_rate),
        "applied": list(applied.descriptions),
        **_shape_comparison(comparison),
        "persisted": False,
    }


def _changes(arguments: Mapping[str, Any]) -> list[Any]:
    changes = arguments.get(CHANGES_KEY)
    if not isinstance(changes, list) or not changes:
        raise ArgumentError(f"{CHANGES_KEY} must be a non-empty list of changes, not {changes!r}.")
    return changes


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
