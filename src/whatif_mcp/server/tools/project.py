from typing import Any

from mcp import types

from whatif_mcp.core.money import round_money
from whatif_mcp.core.projection import Projection
from whatif_mcp.server.operations import inflation as operations
from whatif_mcp.server.operations.projection import (
    check_has_accounts,
    parse_project_arguments,
    project_with_options,
)
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import PROJECTION_OPTION_PROPERTIES, shape_horizon, shape_values
from whatif_mcp.server.tools.writing import write_model_file
from whatif_mcp.store import load_model, resolve_model_path

PROJECT_DESCRIPTION = (
    "Project every account's balance and net worth forward from today, one row per period, "
    "with a summary per account and the total each flow moves."
)

SET_INFLATION_RATE_DESCRIPTION = (
    "Set the model's annual inflation rate, used by project with in_todays_money. "
    "A decimal: 0.03 means 3%."
)

PROJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": PROJECTION_OPTION_PROPERTIES,
    "additionalProperties": False,
}

SET_INFLATION_RATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rate": {"type": "number", "description": "Annual inflation rate as a decimal."},
    },
    "required": ["rate"],
    "additionalProperties": False,
}


def project_model(call: ToolCall) -> dict[str, Any]:
    given = parse_project_arguments(call.arguments)
    model = load_model(resolve_model_path())
    check_has_accounts(model)
    projection = project_with_options(model, call.today, given)
    return _shape_projection(projection, given.years, shape_values(given, model.inflation_rate))


def set_inflation_rate(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    model = load_model(path)
    changed = operations.set_inflation_rate(model, call.arguments)
    result = {"inflation_rate": changed.inflation_rate, "previous": model.inflation_rate}
    write_model_file(path, changed)
    return result


def _shape_projection(projection: Projection, years: int, values: dict[str, Any]) -> dict[str, Any]:
    return {
        **shape_horizon(projection, years),
        **values,
        "periods": [
            {
                "period": row.label,
                "end_date": row.end_date.isoformat(),
                "net_worth": round_money(row.net_worth),
                "balances": {name: round_money(value) for name, value in row.balances.items()},
            }
            for row in projection.periods
        ],
        "accounts": [
            {
                "name": summary.name,
                "kind": summary.kind.value,
                "start_balance": round_money(summary.start_balance),
                "end_balance": round_money(summary.end_balance),
                "reaches_zero": None
                if summary.reaches_zero is None
                else summary.reaches_zero.isoformat(),
                "growth_total": round_money(summary.growth_total),
            }
            for summary in projection.accounts
        ],
        "flows": [
            {"name": total.name, "total": round_money(total.total)} for total in projection.flows
        ],
    }


TOOLS = (
    RegisteredTool(
        types.Tool(name="project", description=PROJECT_DESCRIPTION, input_schema=PROJECT_SCHEMA),
        project_model,
    ),
    RegisteredTool(
        types.Tool(
            name="set_inflation_rate",
            description=SET_INFLATION_RATE_DESCRIPTION,
            input_schema=SET_INFLATION_RATE_SCHEMA,
        ),
        set_inflation_rate,
    ),
)
