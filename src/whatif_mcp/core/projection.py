import calendar
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from whatif_mcp.core.model import AccountKind, Flow, Model
from whatif_mcp.core.recurrence import occurrence_dates

MONTHS_PER_QUARTER = 3
LAST_MONTH = 12


class Granularity(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass(frozen=True)
class PeriodRow:
    label: str
    end_date: date
    balances: Mapping[str, float]
    net_worth: float


@dataclass(frozen=True)
class FlowTotal:
    name: str
    total: float


@dataclass(frozen=True)
class Projection:
    today: date
    horizon_end: date
    granularity: Granularity
    periods: tuple[PeriodRow, ...]
    flows: tuple[FlowTotal, ...]


def horizon_end_date(today: date, years: int) -> date:
    year = today.year + years
    return date(year, today.month, min(today.day, calendar.monthrange(year, today.month)[1]))


def project(model: Model, today: date, horizon_end: date, granularity: Granularity) -> Projection:
    simulation = _Simulation(model, today, horizon_end)
    periods = []
    for label, period_end in _periods(today, horizon_end, granularity):
        simulation.run_through(period_end)
        periods.append(simulation.row(label, period_end))
    flows = tuple(FlowTotal(flow.name, simulation.flow_totals[flow.name]) for flow in model.flows)
    return Projection(today, horizon_end, granularity, tuple(periods), flows)


class _Simulation:
    def __init__(self, model: Model, today: date, horizon_end: date) -> None:
        self._model = model
        self._kinds = {account.name: account.kind for account in model.accounts}
        self.balances = {account.name: account.balance for account in model.accounts}
        self.flow_totals = {flow.name: 0.0 for flow in model.flows}
        self._events = _scheduled_flows(model, today, horizon_end)
        self._event_dates = sorted(self._events)
        self._next_event = 0

    def run_through(self, last_day: date) -> None:
        while (
            self._next_event < len(self._event_dates)
            and self._event_dates[self._next_event] <= last_day
        ):
            for flow in self._events[self._event_dates[self._next_event]]:
                self._apply(flow)
            self._next_event += 1

    def row(self, label: str, end_date: date) -> PeriodRow:
        net_worth = sum(
            balance if self._kinds[name] is AccountKind.ASSET else -balance
            for name, balance in self.balances.items()
        )
        return PeriodRow(label, end_date, dict(self.balances), net_worth)

    def _apply(self, flow: Flow) -> None:
        amount = flow.amount or 0.0
        if flow.from_account is not None:
            self.balances[flow.from_account] -= amount
        if flow.to_account is not None:
            self.balances[flow.to_account] += amount
        self.flow_totals[flow.name] += amount


def _scheduled_flows(model: Model, today: date, horizon_end: date) -> dict[date, list[Flow]]:
    events: dict[date, list[Flow]] = {}
    for flow in model.flows:
        end = horizon_end if flow.end_date is None else min(flow.end_date, horizon_end)
        for occurrence in occurrence_dates(flow.start_date, flow.frequency, end):
            if occurrence > today:
                events.setdefault(occurrence, []).append(flow)
    return events


def _periods(today: date, horizon_end: date, granularity: Granularity) -> Iterator[tuple[str, date]]:
    year, month = today.year, today.month
    while True:
        label, last_month = _period_containing(year, month, granularity)
        period_end = date(year, last_month, calendar.monthrange(year, last_month)[1])
        yield label, min(period_end, horizon_end)
        if period_end >= horizon_end:
            return
        year, month = (year + 1, 1) if last_month == LAST_MONTH else (year, last_month + 1)


def _period_containing(year: int, month: int, granularity: Granularity) -> tuple[str, int]:
    if granularity is Granularity.MONTHLY:
        return f"{year}-{month:02d}", month
    if granularity is Granularity.QUARTERLY:
        quarter = (month - 1) // MONTHS_PER_QUARTER + 1
        return f"{year}-Q{quarter}", quarter * MONTHS_PER_QUARTER
    return f"{year}", LAST_MONTH
