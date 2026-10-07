import calendar
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model
from whatif_mcp.core.recurrence import occurrence_dates

MONTHS_PER_QUARTER = 3
MONTHS_PER_YEAR = 12
LAST_MONTH = 12
GROWTH_DAY = 1

OCCURRENCES_PER_YEAR = {
    Frequency.WEEKLY: 52,
    Frequency.BIWEEKLY: 26,
    Frequency.SEMIMONTHLY: 24,
    Frequency.MONTHLY: 12,
    Frequency.QUARTERLY: 4,
    Frequency.SEMIANNUAL: 2,
    Frequency.ANNUAL: 1,
    Frequency.ONE_TIME: 1,
}


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
class AccountSummary:
    name: str
    kind: AccountKind
    start_balance: float
    end_balance: float
    reaches_zero: date | None
    growth_total: float


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
    accounts: tuple[AccountSummary, ...]
    flows: tuple[FlowTotal, ...]


def horizon_end_date(today: date, years: int) -> date:
    year = today.year + years
    return date(year, today.month, min(today.day, calendar.monthrange(year, today.month)[1]))


def monthly_growth(account: Account, balance: float) -> float:
    if balance <= 0:
        return 0.0
    if account.kind is AccountKind.ASSET:
        return balance * ((1 + account.growth_rate) ** (1 / MONTHS_PER_YEAR) - 1)
    return balance * account.growth_rate / MONTHS_PER_YEAR


def project(model: Model, today: date, horizon_end: date, granularity: Granularity) -> Projection:
    simulation = _Simulation(model, today, horizon_end)
    periods = []
    for label, period_end in _periods(today, horizon_end, granularity):
        simulation.run_through(period_end)
        periods.append(simulation.row(label, period_end))
    accounts = tuple(
        AccountSummary(
            account.name,
            account.kind,
            account.balance,
            simulation.balances[account.name],
            simulation.reaches_zero.get(account.name),
            simulation.growth_totals[account.name],
        )
        for account in model.accounts
    )
    flows = tuple(FlowTotal(flow.name, simulation.flow_totals[flow.name]) for flow in model.flows)
    return Projection(today, horizon_end, granularity, tuple(periods), accounts, flows)


class _Simulation:
    def __init__(self, model: Model, today: date, horizon_end: date) -> None:
        self._model = model
        self._kinds = {account.name: account.kind for account in model.accounts}
        self.balances = {account.name: account.balance for account in model.accounts}
        self.flow_totals = {flow.name: 0.0 for flow in model.flows}
        self.growth_totals = {account.name: 0.0 for account in model.accounts}
        self.reaches_zero: dict[str, date] = {}
        self._events = _scheduled_flows(model, today, horizon_end)
        self._event_dates = sorted(self._events)
        self._next_event = 0

    def run_through(self, last_day: date) -> None:
        while (
            self._next_event < len(self._event_dates)
            and self._event_dates[self._next_event] <= last_day
        ):
            event_date = self._event_dates[self._next_event]
            balances_before = dict(self.balances)
            if event_date.day == GROWTH_DAY:
                self._grow()
            for flow in self._events[event_date]:
                self._apply(flow)
            self._record_reaches_zero(event_date, balances_before)
            self._next_event += 1

    def row(self, label: str, end_date: date) -> PeriodRow:
        net_worth = sum(
            balance if self._kinds[name] is AccountKind.ASSET else -balance
            for name, balance in self.balances.items()
        )
        return PeriodRow(label, end_date, dict(self.balances), net_worth)

    def _grow(self) -> None:
        for account in self._model.accounts:
            growth = monthly_growth(account, self.balances[account.name])
            self.balances[account.name] += growth
            self.growth_totals[account.name] += growth

    def _apply(self, flow: Flow) -> None:
        amount = self._occurrence_amount(flow)
        if flow.to_account is not None and self._kinds[flow.to_account] is AccountKind.LIABILITY:
            amount = max(0.0, min(amount, self.balances[flow.to_account]))
        if flow.from_account is not None:
            self._move(flow.from_account, -amount)
        if flow.to_account is not None:
            self._move(flow.to_account, amount)
        self.flow_totals[flow.name] += amount

    def _occurrence_amount(self, flow: Flow) -> float:
        if flow.amount is not None:
            return flow.amount
        assert flow.rate is not None and flow.rate_of is not None
        base = max(0.0, self.balances[flow.rate_of])
        return flow.rate * base / OCCURRENCES_PER_YEAR[flow.frequency]

    def _move(self, account: str, inflow: float) -> None:
        if self._kinds[account] is AccountKind.ASSET:
            self.balances[account] += inflow
        else:
            self.balances[account] -= inflow

    def _record_reaches_zero(self, event_date: date, balances_before: Mapping[str, float]) -> None:
        for name, balance in self.balances.items():
            if name not in self.reaches_zero and balances_before[name] > 0 and balance <= 0:
                self.reaches_zero[name] = event_date


def _scheduled_flows(model: Model, today: date, horizon_end: date) -> dict[date, list[Flow]]:
    events: dict[date, list[Flow]] = {
        growth_date: [] for growth_date in _growth_dates(today, horizon_end)
    }
    for flow in model.flows:
        end = horizon_end if flow.end_date is None else min(flow.end_date, horizon_end)
        for occurrence in occurrence_dates(flow.start_date, flow.frequency, end):
            if occurrence > today:
                events.setdefault(occurrence, []).append(flow)
    return events


def _growth_dates(today: date, horizon_end: date) -> Iterator[date]:
    first_after_today = date(today.year, today.month, GROWTH_DAY)
    if first_after_today <= today:
        first_after_today = _next_month_start(first_after_today)
    growth_date = first_after_today
    while growth_date <= horizon_end:
        yield growth_date
        growth_date = _next_month_start(growth_date)


def _next_month_start(month_start: date) -> date:
    if month_start.month == LAST_MONTH:
        return date(month_start.year + 1, 1, GROWTH_DAY)
    return date(month_start.year, month_start.month + 1, GROWTH_DAY)


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
