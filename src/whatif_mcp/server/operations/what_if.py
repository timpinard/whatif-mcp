import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from whatif_mcp.core.comparison import EntryMatch
from whatif_mcp.core.model import Model
from whatif_mcp.server.operations import accounts, flows
from whatif_mcp.server.shaping import shape_account, shape_flow

OP_KEY = "op"
NAME_KEY = "name"
MONEY_KEYS = frozenset({"balance", "amount"})


@dataclass(frozen=True)
class AppliedChanges:
    model: Model
    descriptions: tuple[str, ...]
    account_matches: tuple[EntryMatch, ...]
    flow_matches: tuple[EntryMatch, ...]


@dataclass(frozen=True)
class _AppliedChange:
    model: Model
    description: str


def apply_changes(
    model: Model, changes: Sequence[Mapping[str, Any]], today: date
) -> AppliedChanges:
    changed = model
    descriptions = []
    for change in changes:
        applied = _apply(changed, change, today)
        changed = applied.model
        descriptions.append(applied.description)
    return AppliedChanges(
        changed,
        tuple(descriptions),
        match_by_name(
            [account.name for account in model.accounts],
            [account.name for account in changed.accounts],
        ),
        match_by_name([flow.name for flow in model.flows], [flow.name for flow in changed.flows]),
    )


def match_by_name(
    baseline_names: Sequence[str], hypothetical_names: Sequence[str]
) -> tuple[EntryMatch, ...]:
    on_both_sides = set(baseline_names) & set(hypothetical_names)
    baseline = (
        EntryMatch(name, name if name in on_both_sides else None) for name in baseline_names
    )
    new = (EntryMatch(None, name) for name in hypothetical_names if name not in on_both_sides)
    return (*baseline, *new)


def _apply(model: Model, change: Mapping[str, Any], today: date) -> _AppliedChange:
    op = change[OP_KEY]
    arguments = {key: value for key, value in change.items() if key != OP_KEY}
    if op == "set_account":
        account_edit = accounts.set_account(model, arguments, today)
        previous = None if account_edit.previous is None else shape_account(account_edit.previous)
        return _AppliedChange(
            account_edit.model,
            _describe_set(op, previous, shape_account(account_edit.account), arguments),
        )
    if op == "set_flow":
        flow_edit = flows.set_flow(model, arguments, today)
        earlier = None if flow_edit.previous is None else shape_flow(flow_edit.previous)
        return _AppliedChange(
            flow_edit.model, _describe_set(op, earlier, shape_flow(flow_edit.flow), arguments)
        )
    if op == "remove_account":
        account_removal = accounts.remove_account(model, arguments)
        return _AppliedChange(account_removal.model, f"{op} '{account_removal.account.name}'")
    flow_removal = flows.remove_flow(model, arguments)
    return _AppliedChange(flow_removal.model, f"{op} '{flow_removal.flow.name}'")


def _describe_set(
    op: str,
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    given: Mapping[str, Any],
) -> str:
    if previous is None:
        values = (
            f"{key} {_value(key, current[key])}"
            for key in current
            if key in given and key != NAME_KEY
        )
        return f"{op} '{current[NAME_KEY]}': created with {', '.join(values)}"
    changes = [
        f"{key} {_value(key, previous[key])} -> {_value(key, current[key])}"
        for key in current
        if previous[key] != current[key]
    ]
    return f"{op} '{previous[NAME_KEY]}': {', '.join(changes) or 'no change'}"


def _value(key: str, value: Any) -> str:
    if key in MONEY_KEYS and value is not None:
        return f"{value:.2f}"
    return json.dumps(value)
