from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from typing import Any

from whatif_mcp.core.model import Flow, Frequency, Model
from whatif_mcp.core.validation import check_fires, check_flow
from whatif_mcp.server.operations.arguments import (
    ArgumentError,
    optional_choice,
    optional_date,
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


class Omitted(Enum):
    OMITTED = "omitted"


OMITTED = Omitted.OMITTED


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


@dataclass(frozen=True)
class _FlowArguments:
    name: str
    from_account: str | None | Omitted
    to_account: str | None | Omitted
    amount: float | None
    rate: float | None
    rate_of: str | None
    frequency: Frequency | None
    start_date: date | None
    end_date: date | None | Omitted
    new_name: str | None

    @property
    def is_schedule_given(self) -> bool:
        return self.frequency is not None or self.start_date is not None


def set_flow(model: Model, arguments: Mapping[str, Any], today: date) -> FlowEdit:
    given = _parse(model, arguments)
    existing = find_named(model.flows, given.name)
    if existing is None:
        if given.new_name is not None:
            raise ArgumentError(
                f'new_name renames an existing flow, and "{given.name}" does not exist. '
                "To create a flow, give its name as name."
            )
        flow = _applied(_new_flow(model, given, today), given)
    else:
        flow = _applied(existing, given)
        if given.new_name is not None:
            _check_free_name(model, existing, given.new_name)
            flow = replace(flow, name=given.new_name)
    check_flow(flow)
    if given.is_schedule_given:
        check_fires(flow, today)
    changed = _with_flow(model, existing, flow)
    return FlowEdit(changed, flow, existing, _similar_flows(changed, flow))


def remove_flow(model: Model, arguments: Mapping[str, Any]) -> FlowRemoval:
    name = clean_name("name", required_text(arguments, "name"))
    flow = resolve_named("flow", model.flows, name, "name")
    remaining = tuple(other for other in model.flows if other.name != flow.name)
    return FlowRemoval(replace(model, flows=remaining), flow)


def _parse(model: Model, arguments: Mapping[str, Any]) -> _FlowArguments:
    name = clean_name("name", required_text(arguments, "name"))
    new_name = optional_text(arguments, "new_name")
    rate_of = _account(model, arguments, "rate_of")
    return _FlowArguments(
        name=name,
        from_account=_side(model, arguments, "from"),
        to_account=_side(model, arguments, "to"),
        amount=optional_number(arguments, "amount"),
        rate=optional_number(arguments, "rate"),
        rate_of=None if rate_of is OMITTED else rate_of,
        frequency=optional_choice(arguments, "frequency", Frequency),
        start_date=optional_date(arguments, "start_date"),
        end_date=_end_date(arguments),
        new_name=None if new_name is None else clean_name("new_name", new_name),
    )


def _side(model: Model, arguments: Mapping[str, Any], key: str) -> str | None | Omitted:
    if key in arguments and arguments[key] is None:
        return None
    return _account(model, arguments, key)


def _account(model: Model, arguments: Mapping[str, Any], key: str) -> str | Omitted:
    text = optional_text(arguments, key)
    if text is None:
        return OMITTED
    return resolve_named("account", model.accounts, clean_name(key, text), key).name


def _end_date(arguments: Mapping[str, Any]) -> date | None | Omitted:
    if "end_date" not in arguments:
        return OMITTED
    if arguments["end_date"] is None:
        return None
    return optional_date(arguments, "end_date")


def _new_flow(model: Model, given: _FlowArguments, today: date) -> Flow:
    if given.frequency is None:
        raise UnknownNameError(
            f'name: the flow "{given.name}" does not exist. Flow names: '
            f"{name_list(model.flows)}. Give frequency and an amount, or a rate with rate_of, "
            "to create a new flow."
        )
    return Flow(
        name=given.name,
        from_account=None,
        to_account=None,
        amount=None,
        rate=None,
        rate_of=None,
        frequency=given.frequency,
        start_date=today,
    )


def _applied(flow: Flow, given: _FlowArguments) -> Flow:
    amount, rate, rate_of = _size(flow, given)
    return replace(
        flow,
        from_account=_kept(flow.from_account, given.from_account),
        to_account=_kept(flow.to_account, given.to_account),
        amount=amount,
        rate=rate,
        rate_of=rate_of,
        frequency=given.frequency or flow.frequency,
        start_date=given.start_date or flow.start_date,
        end_date=_kept(flow.end_date, given.end_date),
    )


def _size(flow: Flow, given: _FlowArguments) -> tuple[float | None, float | None, str | None]:
    if given.amount is None and given.rate is None:
        return flow.amount, flow.rate, given.rate_of or flow.rate_of
    if given.rate is None:
        return given.amount, None, given.rate_of
    return given.amount, given.rate, given.rate_of or flow.rate_of


def _kept[ValueT](current: ValueT, given: ValueT | Omitted) -> ValueT:
    return current if isinstance(given, Omitted) else given


def _check_free_name(model: Model, existing: Flow, new_name: str) -> None:
    holder = find_named(model.flows, new_name)
    if holder is not None and holder.name != existing.name:
        raise ArgumentError(
            f'new_name: a flow named "{holder.name}" already exists (names ignore case). '
            "Choose another name."
        )


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
