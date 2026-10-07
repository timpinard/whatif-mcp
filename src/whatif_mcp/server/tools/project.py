from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from mcp import types

from whatif_mcp.core.model import Model
from whatif_mcp.core.projection import Granularity, Projection, horizon_end_date, project
from whatif_mcp.core.todays_money import in_todays_money
from whatif_mcp.server.operations import inflation as operations
from whatif_mcp.server.operations.arguments import (
    ArgumentError,
    optional_boolean,
    optional_choice,
    optional_number,
)
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import round_money
from whatif_mcp.server.tools.writing import write_model_file
from whatif_mcp.store import load_model, resolve_model_path

DEFAULT_HORIZON_YEARS = 5
DEFAULT_GRANULARITY = Granularity.ANNUAL
MIN_HORIZON_YEARS = 1
MAX_HORIZON_YEARS = 50
MAX_MONTHLY_HORIZON_YEARS = 10
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


@dataclass(frozen=True)
class _ProjectArguments:
    years: int
    granularity: Granularity
    is_todays_money: bool


def project_model(call: ToolCall) -> dict[str, Any]:
    given = _parse(call.arguments)
    model = load_model(resolve_model_path())
    _check_has_accounts(model)
    horizon_end = horizon_end_date(call.today, given.years)
    projection = project(model, call.today, horizon_end, given.granularity)
    if not given.is_todays_money:
        return _shape_projection(projection, given.years, {"values": NOMINAL})
    values = {"values": TODAYS_MONEY, "inflation_rate": model.inflation_rate}
    return _shape_projection(in_todays_money(projection, model.inflation_rate), given.years, values)


def set_inflation_rate(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    model = load_model(path)
    changed = operations.set_inflation_rate(model, call.arguments)
    write_model_file(path, changed)
    return {"inflation_rate": changed.inflation_rate, "previous": model.inflation_rate}


def _parse(arguments: Mapping[str, Any]) -> _ProjectArguments:
    years = _horizon_years(arguments)
    granularity = optional_choice(arguments, "granularity", Granularity) or DEFAULT_GRANULARITY
    if granularity is Granularity.MONTHLY and years > MAX_MONTHLY_HORIZON_YEARS:
        raise ArgumentError(
            f"granularity monthly is allowed only for horizons of {MAX_MONTHLY_HORIZON_YEARS} "
            f"years or less, and horizon_years is {years}: use quarterly or annual."
        )
    is_todays_money = optional_boolean(arguments, "in_todays_money") or False
    return _ProjectArguments(years, granularity, is_todays_money)


def _horizon_years(arguments: Mapping[str, Any]) -> int:
    years = optional_number(arguments, "horizon_years")
    if years is None:
        return DEFAULT_HORIZON_YEARS
    if not years.is_integer() or not MIN_HORIZON_YEARS <= years <= MAX_HORIZON_YEARS:
        raise ArgumentError(
            f"horizon_years {years:g} is not allowed: give a whole number of years from "
            f"{MIN_HORIZON_YEARS} to {MAX_HORIZON_YEARS}."
        )
    return int(years)


def _check_has_accounts(model: Model) -> None:
    if not model.accounts:
        raise ArgumentError("The model has no accounts to project. Add one with set_account first.")


def _shape_projection(projection: Projection, years: int, values: dict[str, Any]) -> dict[str, Any]:
    return {
        "today": projection.today.isoformat(),
        "horizon": {
            "years": years,
            "from": projection.periods[0].label,
            "to": projection.periods[-1].label,
            "end_date": projection.horizon_end.isoformat(),
        },
        "granularity": projection.granularity.value,
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
