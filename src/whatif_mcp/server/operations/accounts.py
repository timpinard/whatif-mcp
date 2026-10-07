from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from whatif_mcp.core.model import Account, AccountKind, Flow, Model
from whatif_mcp.core.rules import check_account
from whatif_mcp.server.operations.arguments import (
    ArgumentError,
    optional_choice,
    optional_number,
    optional_text,
    required_text,
)
from whatif_mcp.server.operations.names import (
    UnknownNameError,
    clean_name,
    find_named,
    name_list,
    resolve_named,
)


@dataclass(frozen=True)
class AccountEdit:
    model: Model
    account: Account
    previous: Account | None


@dataclass(frozen=True)
class AccountRemoval:
    model: Model
    account: Account


@dataclass(frozen=True)
class _AccountArguments:
    name: str
    kind: AccountKind | None
    balance: float | None
    growth_rate: float | None
    volatility: float | None
    new_name: str | None


def set_account(model: Model, arguments: Mapping[str, Any], today: date) -> AccountEdit:
    given = _parse(arguments)
    existing = find_named(model.accounts, given.name)
    if existing is None:
        account = replace(_new_account(model, given, today), **_updates(given, today))
    else:
        account = replace(existing, **_updates(given, today))
        if given.new_name is not None:
            _check_free_name(model, existing, given.new_name)
            account = replace(account, name=given.new_name)
    check_account(account)
    return AccountEdit(_with_account(model, existing, account), account, existing)


def remove_account(model: Model, arguments: Mapping[str, Any]) -> AccountRemoval:
    name = clean_name("name", required_text(arguments, "name"))
    account = resolve_named("account", model.accounts, name, "name")
    users = [flow.name for flow in model.flows if account.name in _account_references(flow)]
    if users:
        raise ArgumentError(
            f'name: the account "{account.name}" is used by the flows {", ".join(users)}. '
            "Remove them with remove_flow or move them to another account with set_flow first."
        )
    remaining = tuple(other for other in model.accounts if other.name != account.name)
    return AccountRemoval(replace(model, accounts=remaining), account)


def _parse(arguments: Mapping[str, Any]) -> _AccountArguments:
    new_name = optional_text(arguments, "new_name")
    return _AccountArguments(
        name=clean_name("name", required_text(arguments, "name")),
        kind=optional_choice(arguments, "kind", AccountKind),
        balance=optional_number(arguments, "balance"),
        growth_rate=optional_number(arguments, "growth_rate"),
        volatility=optional_number(arguments, "volatility"),
        new_name=None if new_name is None else clean_name("new_name", new_name),
    )


def _new_account(model: Model, given: _AccountArguments, today: date) -> Account:
    if given.kind is None:
        raise UnknownNameError(
            f'name: the account "{given.name}" does not exist. Account names: '
            f"{name_list(model.accounts)}. Give kind and balance to create a new account."
        )
    if given.balance is None:
        raise ArgumentError(
            f'balance is required to create the account "{given.name}": give its balance today.'
        )
    if given.new_name is not None:
        raise ArgumentError(
            f'new_name renames an existing account, and "{given.name}" does not exist. '
            "To create an account, give its name as name."
        )
    return Account(given.name, given.kind, given.balance, today)


def _updates(given: _AccountArguments, today: date) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if given.kind is not None:
        updates["kind"] = given.kind
    if given.balance is not None:
        updates["balance"] = given.balance
        updates["balance_as_of"] = today
    if given.growth_rate is not None:
        updates["growth_rate"] = given.growth_rate
    if given.volatility is not None:
        updates["volatility"] = given.volatility
    return updates


def _check_free_name(model: Model, existing: Account, new_name: str) -> None:
    holder = find_named(model.accounts, new_name)
    if holder is not None and holder.name != existing.name:
        raise ArgumentError(
            f'new_name: an account named "{holder.name}" already exists (names ignore case). '
            "Choose another name."
        )


def _with_account(model: Model, existing: Account | None, account: Account) -> Model:
    if existing is None:
        return replace(model, accounts=(*model.accounts, account))
    accounts = tuple(account if other.name == existing.name else other for other in model.accounts)
    flows = tuple(_renamed_references(flow, existing.name, account.name) for flow in model.flows)
    return replace(model, accounts=accounts, flows=flows)


def _renamed_references(flow: Flow, old_name: str, new_name: str) -> Flow:
    def renamed(reference: str | None) -> str | None:
        return new_name if reference == old_name else reference

    return replace(
        flow,
        from_account=renamed(flow.from_account),
        to_account=renamed(flow.to_account),
        rate_of=renamed(flow.rate_of),
    )


def _account_references(flow: Flow) -> tuple[str | None, ...]:
    return (flow.from_account, flow.to_account, flow.rate_of)
