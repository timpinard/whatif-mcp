from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from whatif_mcp.core.money import round_money
from whatif_mcp.core.projection import AccountSummary, Projection


@dataclass(frozen=True)
class EntryMatch:
    baseline_name: str | None
    hypothetical_name: str | None

    @property
    def name(self) -> str:
        if self.hypothetical_name is not None:
            return self.hypothetical_name
        if self.baseline_name is not None:
            return self.baseline_name
        raise ValueError("an entry is on at least one side")


@dataclass(frozen=True)
class NetWorthDifference:
    label: str
    end_date: date
    baseline: float
    hypothetical: float
    difference: float


@dataclass(frozen=True)
class AccountComparison:
    name: str
    baseline: AccountSummary | None
    hypothetical: AccountSummary | None
    end_difference: float
    growth_difference: float


@dataclass(frozen=True)
class FlowComparison:
    name: str
    baseline_total: float
    hypothetical_total: float
    difference: float


@dataclass(frozen=True)
class Comparison:
    net_worth: tuple[NetWorthDifference, ...]
    end_difference: float
    accounts: tuple[AccountComparison, ...]
    flows: tuple[FlowComparison, ...]


def compare(
    baseline: Projection,
    hypothetical: Projection,
    account_matches: Sequence[EntryMatch],
    flow_matches: Sequence[EntryMatch],
) -> Comparison:
    net_worth = tuple(
        NetWorthDifference(
            before.label,
            before.end_date,
            before.net_worth,
            after.net_worth,
            after.net_worth - before.net_worth,
        )
        for before, after in zip(baseline.periods, hypothetical.periods, strict=True)
    )
    return Comparison(
        net_worth,
        net_worth[-1].difference,
        _compare_accounts(baseline, hypothetical, account_matches),
        _compare_flows(baseline, hypothetical, flow_matches),
    )


def _compare_accounts(
    baseline: Projection, hypothetical: Projection, matches: Sequence[EntryMatch]
) -> tuple[AccountComparison, ...]:
    baseline_summaries = _summaries_by_name(baseline)
    hypothetical_summaries = _summaries_by_name(hypothetical)
    comparisons = []
    for match in matches:
        before = _side(baseline_summaries, match.baseline_name)
        after = _side(hypothetical_summaries, match.hypothetical_name)
        comparisons.append(
            AccountComparison(
                match.name,
                before,
                after,
                _end_balance(after) - _end_balance(before),
                _growth_total(after) - _growth_total(before),
            )
        )
    return tuple(comparisons)


def _compare_flows(
    baseline: Projection, hypothetical: Projection, matches: Sequence[EntryMatch]
) -> tuple[FlowComparison, ...]:
    baseline_totals = {total.name: total.total for total in baseline.flows}
    hypothetical_totals = {total.name: total.total for total in hypothetical.flows}
    comparisons = []
    for match in matches:
        before = _side(baseline_totals, match.baseline_name) or 0.0
        after = _side(hypothetical_totals, match.hypothetical_name) or 0.0
        if round_money(before) != round_money(after):
            comparisons.append(FlowComparison(match.name, before, after, after - before))
    return tuple(comparisons)


def _summaries_by_name(projection: Projection) -> dict[str, AccountSummary]:
    return {summary.name: summary for summary in projection.accounts}


def _side[EntryT](entries: Mapping[str, EntryT], name: str | None) -> EntryT | None:
    return None if name is None else entries[name]


def _end_balance(summary: AccountSummary | None) -> float:
    return 0.0 if summary is None else summary.end_balance


def _growth_total(summary: AccountSummary | None) -> float:
    return 0.0 if summary is None else summary.growth_total


def difference_values(comparison: Comparison) -> Iterator[float]:
    for row in comparison.net_worth:
        yield row.difference
    for account in comparison.accounts:
        yield from (account.end_difference, account.growth_difference)
    for flow in comparison.flows:
        yield flow.difference
