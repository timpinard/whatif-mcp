from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from whatif_mcp.core.errors import ValidationError
from whatif_mcp.core.model import Model
from whatif_mcp.core.validation import check_inflation_rate
from whatif_mcp.server.operations.arguments import ArgumentError, required_number


def set_inflation_rate(model: Model, arguments: Mapping[str, Any]) -> Model:
    rate = required_number(arguments, "rate")
    try:
        check_inflation_rate(rate)
    except ValidationError as error:
        raise ArgumentError(f"rate {error}.") from error
    return replace(model, inflation_rate=rate)
