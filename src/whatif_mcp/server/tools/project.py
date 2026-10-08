from typing import Any

from mcp import types

from whatif_mcp.core.money import round_money
from whatif_mcp.core.projection import Granularity, Projection, horizon_end_date, project
from whatif_mcp.core.todays_money import in_todays_money
from whatif_mcp.server.operations import inflation as operations
from whatif_mcp.server.operations.projection import (
    DEFAULT_GRANULARITY,
    DEFAULT_HORIZON_YEARS,
    MAX_HORIZON_YEARS,
    MAX_MONTHLY_HORIZON_YEARS,
    MIN_HORIZON_YEARS,
    check_has_accounts,
    check_reportable,
    parse_project_arguments,
)
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import shape_horizon
from whatif_mcp.server.tools.writing import write_model_file
from whatif_mcp.store import load_model, resolve_model_path

NOMINAL = "nominal"
TODAYS_MONEY = "todays_money"

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
    "properties": {
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
    },
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
    horizon_end = horizon_end_date(call.today, given.years)
    projection = project(model, call.today, horizon_end, given.granularity)
    values: dict[str, Any] = {"values": NOMINAL}
    if given.is_todays_money:
        projection = in_todays_money(projection, model.inflation_rate)
        values = {"values": TODAYS_MONEY, "inflation_rate": model.inflation_rate}
    check_reportable(projection)
    return _shape_projection(projection, given.years, values)


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
