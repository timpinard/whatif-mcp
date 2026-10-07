from collections.abc import Iterable, Sequence
from typing import Protocol

from whatif_mcp.core.errors import WhatIfError
from whatif_mcp.server.operations.arguments import ArgumentError


class UnknownNameError(WhatIfError):
    pass


class Named(Protocol):
    @property
    def name(self) -> str: ...


def clean_name(argument: str, value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ArgumentError(f"{argument} is blank: give a name.")
    return trimmed


def find_named[NamedT: Named](items: Iterable[NamedT], name: str) -> NamedT | None:
    wanted = _matching_key(name)
    return next((item for item in items if _matching_key(item.name) == wanted), None)


def resolve_named[NamedT: Named](
    entity: str, items: Sequence[NamedT], name: str, argument: str
) -> NamedT:
    found = find_named(items, name)
    if found is None:
        raise UnknownNameError(
            f'{argument}: no {entity} is named "{name}". '
            f"{entity.capitalize()} names: {name_list(items)}."
        )
    return found


def name_list(items: Iterable[Named]) -> str:
    return ", ".join(item.name for item in items) or "none"


def _matching_key(name: str) -> str:
    return name.strip().casefold()
