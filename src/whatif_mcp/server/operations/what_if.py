import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from datetime import date
from typing import Any

from whatif_mcp.core.comparison import EntryMatch
from whatif_mcp.core.errors import WhatIfError
from whatif_mcp.core.model import Account, Flow, Model
from whatif_mcp.server.operations import accounts, flows
from whatif_mcp.server.operations.names import matching_key
from whatif_mcp.server.shaping import FLOW_RESULT_KEYS, shape_account, shape_flow

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
    removed: list[tuple[str, _Entry]] = field(default_factory=list)

    @classmethod
    def create(cls, baseline_names: Sequence[str]) -> "_EntryTracker":
        return cls([_Entry(name, name) for name in baseline_names])

    def set(self, previous_name: str | None, name: str) -> None:
        if previous_name is None:
            entry = self._take_resumed(matching_key(name)) or self._added()
        else:
            entry = self._live(previous_name)
        entry.hypothetical_name = name

    def remove(self, name: str) -> None:
        entry = self._live(name)
        entry.hypothetical_name = None
        self.removed.append((matching_key(name), entry))

    def matches(self) -> tuple[EntryMatch, ...]:
        return tuple(
            EntryMatch(entry.baseline_name, entry.hypothetical_name)
            for entry in self.entries
            if entry.baseline_name is not None or entry.hypothetical_name is not None
        )

    def _take_resumed(self, key: str) -> _Entry | None:
        by_baseline_name = (
            entry
            for _, entry in self.removed
            if entry.baseline_name is not None and matching_key(entry.baseline_name) == key
        )
        by_removed_name = (
            entry for removed_key, entry in reversed(self.removed) if removed_key == key
        )
        entry = next(by_baseline_name, None) or next(by_removed_name, None)
        self.removed = [removal for removal in self.removed if removal[1] is not entry]
        return entry

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
        if account_edit.previous is None:
            description = _describe_create(op, _shape_stored(account_edit.account), arguments)
        else:
            description = _describe_update(
                op,
                _shape_stored(account_edit.previous),
                _shape_stored(account_edit.account),
                _changed_keys(account_edit.previous, account_edit.account),
            )
        return _AppliedChange(account_edit.model, description)
    if op == SET_FLOW_OP:
        flow_edit = flows.set_flow(model, arguments, today)
        flow_entries.set(
            None if flow_edit.previous is None else flow_edit.previous.name, flow_edit.flow.name
        )
        if flow_edit.previous is None:
            description = _describe_create(op, _shape_stored(flow_edit.flow), arguments)
        else:
            description = _describe_update(
                op,
                _shape_stored(flow_edit.previous),
                _shape_stored(flow_edit.flow),
                _changed_keys(flow_edit.previous, flow_edit.flow),
            )
        return _AppliedChange(flow_edit.model, description)
    if op == REMOVE_ACCOUNT_OP:
        account_removal = accounts.remove_account(model, arguments)
        account_entries.remove(account_removal.account.name)
        return _AppliedChange(account_removal.model, f"{op} '{account_removal.account.name}'")
    flow_removal = flows.remove_flow(model, arguments)
    flow_entries.remove(flow_removal.flow.name)
    return _AppliedChange(flow_removal.model, f"{op} '{flow_removal.flow.name}'")


def _describe_create(op: str, current: Mapping[str, Any], given: Mapping[str, Any]) -> str:
    values = (
        f"{key} {_value(key, current[key])}" for key in current if key in given and key != NAME_KEY
    )
    return f"{op} '{current[NAME_KEY]}': created with {', '.join(values)}"


def _describe_update(
    op: str, previous: Mapping[str, Any], current: Mapping[str, Any], changed_keys: set[str]
) -> str:
    changes = [
        f"{key} {_value(key, previous[key])} -> {_value(key, current[key])}"
        for key in current
        if key in changed_keys
    ]
    return f"{op} '{previous[NAME_KEY]}': {', '.join(changes) or 'no change'}"


def _changed_keys[EntryT: (Account, Flow)](previous: EntryT, current: EntryT) -> set[str]:
    return {
        FLOW_RESULT_KEYS.get(entry_field.name, entry_field.name)
        for entry_field in fields(current)
        if getattr(previous, entry_field.name) != getattr(current, entry_field.name)
    }


def _shape_stored(entry: Account | Flow) -> dict[str, Any]:
    shaped = shape_account(entry) if isinstance(entry, Account) else shape_flow(entry)
    return {
        key: getattr(entry, key) if key in MONEY_KEYS else value for key, value in shaped.items()
    }


def _value(key: str, value: Any) -> str:
    if key in MONEY_KEYS and value is not None:
        return _money_text(value)
    return json.dumps(value)


def _money_text(value: float) -> str:
    cents_text = f"{value:.2f}"
    return cents_text if float(cents_text) == value else repr(value)
