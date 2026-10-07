from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from whatif_mcp.core.model import Flow, Frequency, Model
from whatif_mcp.core.validation import check_fires, check_flow
from whatif_mcp.server.operations.arguments import (
    ArgumentError,
    optional_choice,
    optional_date,
    optional_number,
    required_text,
)
from whatif_mcp.server.operations.names import (
    UnknownNameError,
    clean_name,
    find_named,
    name_list,
    resolve_named,
)

ACCOUNT_ARGUMENTS = {"from": "from_account", "to": "to_account", "rate_of": "rate_of"}
NULLABLE_ACCOUNT_ARGUMENTS = ("from", "to")


@dataclass(frozen=True)
class FlowEdit:
    model: Model
    flow: Flow
    previous: Flow | None
    similar_flows: tuple[str, ...]


@dataclass(frozen=True)
class FlowRemoval:
    model: Model
    flow: Flow


def set_flow(model: Model, arguments: Mapping[str, Any], today: date) -> FlowEdit:
    name = clean_name("name", required_text(arguments, "name"))
    existing = find_named(model.flows, name)
    updates = {**_account_updates(model, arguments), **_size_updates(arguments)}
    updates |= _schedule_updates(arguments)
    if existing is None:
        flow = replace(_new_flow(model, name, arguments, updates, today), **updates)
    else:
        flow = replace(existing, **updates)
        if "new_name" in arguments:
            flow = replace(flow, name=_free_name(model, existing, arguments))
    check_flow(flow)
    if "start_date" in arguments or "frequency" in arguments:
        check_fires(flow, today)
    changed = _with_flow(model, existing, flow)
    return FlowEdit(changed, flow, existing, _similar_flows(changed, flow))


def remove_flow(model: Model, arguments: Mapping[str, Any]) -> FlowRemoval:
    name = clean_name("name", required_text(arguments, "name"))
    flow = resolve_named("flow", model.flows, name, "name")
    remaining = tuple(other for other in model.flows if other.name != flow.name)
    return FlowRemoval(replace(model, flows=remaining), flow)


def _account_updates(model: Model, arguments: Mapping[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for argument, field_name in ACCOUNT_ARGUMENTS.items():
        if argument not in arguments:
            continue
        if arguments[argument] is None and argument in NULLABLE_ACCOUNT_ARGUMENTS:
            updates[field_name] = None
            continue
        account_name = clean_name(argument, required_text(arguments, argument))
        updates[field_name] = resolve_named("account", model.accounts, account_name, argument).name
    return updates


def _size_updates(arguments: Mapping[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if "amount" in arguments:
        updates["amount"] = optional_number(arguments, "amount")
        if "rate" not in arguments:
            updates |= {"rate": None, "rate_of": None}
    if "rate" in arguments:
        updates["rate"] = optional_number(arguments, "rate")
        if "amount" not in arguments:
            updates["amount"] = None
    return updates


def _schedule_updates(arguments: Mapping[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if "frequency" in arguments:
        updates["frequency"] = optional_choice(arguments, "frequency", Frequency)
    if "start_date" in arguments:
        updates["start_date"] = optional_date(arguments, "start_date")
    if "end_date" in arguments:
        is_cleared = arguments["end_date"] is None
        updates["end_date"] = None if is_cleared else optional_date(arguments, "end_date")
    return updates


def _new_flow(
    model: Model, name: str, arguments: Mapping[str, Any], updates: Mapping[str, Any], today: date
) -> Flow:
    if "frequency" not in updates:
        raise UnknownNameError(
            f'name: the flow "{name}" does not exist. Flow names: {name_list(model.flows)}. '
            "Give frequency and an amount, or a rate with rate_of, to create a new flow."
        )
    if "new_name" in arguments:
        raise ArgumentError(
            f'new_name renames an existing flow, and "{name}" does not exist. '
            "To create a flow, give its name as name."
        )
    return Flow(name, None, None, None, None, None, updates["frequency"], today)


def _free_name(model: Model, existing: Flow, arguments: Mapping[str, Any]) -> str:
    new_name = clean_name("new_name", required_text(arguments, "new_name"))
    holder = find_named(model.flows, new_name)
    if holder is not None and holder.name != existing.name:
        raise ArgumentError(
            f'new_name: a flow named "{holder.name}" already exists (names ignore case). '
            "Choose another name."
        )
    return new_name


def _with_flow(model: Model, existing: Flow | None, flow: Flow) -> Model:
    if existing is None:
        return replace(model, flows=(*model.flows, flow))
    flows = tuple(flow if other.name == existing.name else other for other in model.flows)
    return replace(model, flows=flows)


def _similar_flows(model: Model, flow: Flow) -> tuple[str, ...]:
    return tuple(
        other.name
        for other in model.flows
        if other.name != flow.name
        and (other.from_account, other.to_account, other.frequency)
        == (flow.from_account, flow.to_account, flow.frequency)
    )
