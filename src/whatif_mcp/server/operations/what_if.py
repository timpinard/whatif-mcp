import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from whatif_mcp.core.comparison import EntryMatch
from whatif_mcp.core.errors import WhatIfError
from whatif_mcp.core.model import Model
from whatif_mcp.server.operations import accounts, flows
from whatif_mcp.server.operations.names import matching_key
from whatif_mcp.server.shaping import shape_account, shape_flow

OP_KEY = "op"
SET_ACCOUNT_OP = "set_account"
REMOVE_ACCOUNT_OP = "remove_account"
SET_FLOW_OP = "set_flow"
REMOVE_FLOW_OP = "remove_flow"
OPS = (SET_ACCOUNT_OP, REMOVE_ACCOUNT_OP, SET_FLOW_OP, REMOVE_FLOW_OP)
OPS_LISTED = ", ".join(OPS)
NAME_KEY = "name"
MONEY_KEYS = frozenset({"balance", "amount"})


class ChangeError(WhatIfError):
    pass


@dataclass(frozen=True)
class Change:
    op: str
    arguments: Mapping[str, Any]


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


@dataclass
class _Entry:
    baseline_name: str | None
    hypothetical_name: str | None


@dataclass
class _EntryTracker:
    entries: list[_Entry]
    removed: dict[str, _Entry] = field(default_factory=dict)

    @classmethod
    def create(cls, baseline_names: Sequence[str]) -> "_EntryTracker":
        return cls([_Entry(name, name) for name in baseline_names])

    def set(self, previous_name: str | None, name: str) -> None:
        if previous_name is None:
            entry = self.removed.pop(matching_key(name), None) or self._added()
        else:
            entry = self._live(previous_name)
        entry.hypothetical_name = name

    def remove(self, name: str) -> None:
        entry = self._live(name)
        entry.hypothetical_name = None
        self.removed[matching_key(name)] = entry

    def matches(self) -> tuple[EntryMatch, ...]:
        return tuple(
            EntryMatch(entry.baseline_name, entry.hypothetical_name)
            for entry in self.entries
            if entry.baseline_name is not None or entry.hypothetical_name is not None
        )

    def _added(self) -> _Entry:
        entry = _Entry(None, None)
        self.entries.append(entry)
        return entry

    def _live(self, name: str) -> _Entry:
        return next(entry for entry in self.entries if entry.hypothetical_name == name)


def apply_changes(model: Model, changes: Sequence[Change], today: date) -> AppliedChanges:
    changed = model
    descriptions = []
    account_entries = _EntryTracker.create([account.name for account in model.accounts])
    flow_entries = _EntryTracker.create([flow.name for flow in model.flows])
    for position, change in enumerate(changes, start=1):
        try:
            applied = _apply(changed, change, today, account_entries, flow_entries)
        except WhatIfError as error:
            raise change_error(position, error) from error
        changed = applied.model
        descriptions.append(applied.description)
    return AppliedChanges(
        changed, tuple(descriptions), account_entries.matches(), flow_entries.matches()
    )


def change_error(position: int, error: WhatIfError) -> ChangeError:
    return ChangeError(f"change {position}: {error}")


def _apply(
    model: Model,
    change: Change,
    today: date,
    account_entries: _EntryTracker,
    flow_entries: _EntryTracker,
) -> _AppliedChange:
    op, arguments = change.op, change.arguments
    if op == SET_ACCOUNT_OP:
        account_edit = accounts.set_account(model, arguments, today)
        account_entries.set(
            None if account_edit.previous is None else account_edit.previous.name,
            account_edit.account.name,
        )
        previous = None if account_edit.previous is None else shape_account(account_edit.previous)
        return _AppliedChange(
            account_edit.model,
            _describe_set(op, previous, shape_account(account_edit.account), arguments),
        )
    if op == SET_FLOW_OP:
        flow_edit = flows.set_flow(model, arguments, today)
        flow_entries.set(
            None if flow_edit.previous is None else flow_edit.previous.name, flow_edit.flow.name
        )
        previous = None if flow_edit.previous is None else shape_flow(flow_edit.previous)
        return _AppliedChange(
            flow_edit.model, _describe_set(op, previous, shape_flow(flow_edit.flow), arguments)
        )
    if op == REMOVE_ACCOUNT_OP:
        account_removal = accounts.remove_account(model, arguments)
        account_entries.remove(account_removal.account.name)
        return _AppliedChange(account_removal.model, f"{op} '{account_removal.account.name}'")
    flow_removal = flows.remove_flow(model, arguments)
    flow_entries.remove(flow_removal.flow.name)
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
