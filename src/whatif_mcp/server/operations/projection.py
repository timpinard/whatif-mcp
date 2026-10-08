import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from whatif_mcp.core.errors import WhatIfError
from whatif_mcp.core.model import Model
from whatif_mcp.core.projection import (
    Granularity,
    Projection,
    horizon_end_date,
    money_values,
    project,
)
from whatif_mcp.core.todays_money import in_todays_money
from whatif_mcp.server.operations.arguments import (
    ArgumentError,
    optional_boolean,
    optional_choice,
    optional_number,
)

DEFAULT_HORIZON_YEARS = 5
DEFAULT_GRANULARITY = Granularity.ANNUAL
MIN_HORIZON_YEARS = 1
MAX_HORIZON_YEARS = 50
MAX_MONTHLY_HORIZON_YEARS = 10
MAX_REPORTED_MONEY = 1_000_000_000_000_000


class EmptyModelError(WhatIfError):
    pass


class UnreportableProjectionError(WhatIfError):
    pass


@dataclass(frozen=True)
class ProjectArguments:
    years: int
    granularity: Granularity
    is_todays_money: bool


def parse_project_arguments(arguments: Mapping[str, Any]) -> ProjectArguments:
    years = _horizon_years(arguments)
    granularity = optional_choice(arguments, "granularity", Granularity) or DEFAULT_GRANULARITY
    if granularity is Granularity.MONTHLY and years > MAX_MONTHLY_HORIZON_YEARS:
        raise ArgumentError(
            f"granularity monthly is allowed only for horizons of {MAX_MONTHLY_HORIZON_YEARS} "
            f"years or less, and horizon_years is {years}: use quarterly or annual."
        )
    is_todays_money = optional_boolean(arguments, "in_todays_money") or False
    return ProjectArguments(years, granularity, is_todays_money)


def project_with_options(model: Model, today: date, given: ProjectArguments) -> Projection:
    projection = project(model, today, horizon_end_date(today, given.years), given.granularity)
    if given.is_todays_money:
        projection = in_todays_money(projection, model.inflation_rate)
    check_reportable(projection)
    return projection


def check_has_accounts(model: Model) -> None:
    if not model.accounts:
        raise EmptyModelError(
            "The model has no accounts to project. Add one with set_account first."
        )


def check_hypothetical_has_accounts(model: Model) -> None:
    if not model.accounts:
        raise EmptyModelError(
            "The hypothetical model has no accounts to project: the changes remove every account."
        )


def check_reportable(projection: Projection) -> None:
    check_reportable_values(money_values(projection))


def check_reportable_values(values: Iterable[float]) -> None:
    if all(math.isfinite(value) and abs(value) < MAX_REPORTED_MONEY for value in values):
        return
    raise UnreportableProjectionError(
        f"The projection reaches money values of {MAX_REPORTED_MONEY:,} or more, or values too "
        "large to compute. Reduce horizon_years, or the growth_rate of the accounts that grow "
        "fastest, or the inflation rate (set_inflation_rate) when in_todays_money is true."
    )


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
