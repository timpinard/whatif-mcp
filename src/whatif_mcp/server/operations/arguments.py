from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from whatif_mcp.core.errors import ValidationError, WhatIfError
from whatif_mcp.core.validation import finite_number


class ArgumentError(WhatIfError):
    pass


def required_text(arguments: Mapping[str, Any], key: str) -> str:
    if key not in arguments:
        raise ArgumentError(f"{key} is required.")
    return _text(arguments, key)


def optional_text(arguments: Mapping[str, Any], key: str) -> str | None:
    if key not in arguments:
        return None
    return _text(arguments, key)


def optional_number(arguments: Mapping[str, Any], key: str) -> float | None:
    if key not in arguments:
        return None
    try:
        return finite_number(arguments[key])
    except ValidationError as error:
        raise ArgumentError(f"{key} {error}.") from error


def optional_choice[ChoiceT: StrEnum](
    arguments: Mapping[str, Any], key: str, choices: type[ChoiceT]
) -> ChoiceT | None:
    if key not in arguments:
        return None
    value = arguments[key]
    allowed = ", ".join(choice.value for choice in choices)
    if not isinstance(value, str) or value not in set(choices):
        raise ArgumentError(f"{key} must be one of {allowed}, not {value!r}.")
    return choices(value)


def _text(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments[key]
    if not isinstance(value, str):
        raise ArgumentError(f"{key} must be a string, not {value!r}.")
    return value
