import random
from typing import Any

from mcp import Client
from mcp.types import CallToolResult, TextContent

HOSTILE_SHARE = 0.6
OPTIONAL_ARGUMENT_SHARE = 0.3
UNKNOWN_ARGUMENT_SHARE = 0.05
LONG_TEXT = "x" * 10_000
SHOWN_TEXT_LENGTH = 40
SHOWN_INT_LIMIT = 10**20

ACCOUNT_NAMES = ["Checking", "Savings", "Car loan", " checking ", "CAR LOAN", "New"]
FLOW_NAMES = ["Salary", "Car payment", " salary ", "New flow"]
FLOW_ACCOUNT_NAMES = ["Checking", "Savings", "Car loan", " checking "]
NEW_FLOW_NAMES = ["Bonus", "Salary 2"]
RATES: list[Any] = [0.0, 0.03, 0.07, 1.0, -0.5, -0.99, 0.99, 0.0001, 1e-320]
AMOUNTS: list[Any] = [1, 100.5, 4000, 0.01, 1e-320, 1_000_000_000_000]
DATES = ["2026-10-06", "2026-10-07", "2026-11-01", "2026-12-31", "1900-01-01", "2100-01-01"]
KINDS = ["asset", "liability"]
FREQUENCIES = [
    "weekly",
    "biweekly",
    "semimonthly",
    "monthly",
    "quarterly",
    "semiannual",
    "annual",
    "one_time",
]
GRANULARITIES = ["monthly", "quarterly", "annual"]
HORIZONS: list[Any] = [1, 2, 5, 10, 11, 50]
BOOLEANS = [True, False]

WRONG_TYPES: list[Any] = [True, False, [], [1, "a"], {}, {"a": 1}, None]
ODD_TEXT = ["", " ", "   ", "\t\n", LONG_TEXT, "!@#$%^&*()", "null", "0", "a'); --", "/etc"]
NUMBERS: list[Any] = [
    0,
    -0.0,
    -1,
    7,
    1e308,
    -1e308,
    1e-320,
    -1e-320,
    10**400,
    -(10**400),
    2**63,
    -0.9999999,
    0.9999999999,
    999_999_999_999.99,
]
ODD_DATES = [
    "0001-01-01",
    "1899-12-31",
    "9999-12-31",
    "10/1/2026",
    "2026-02-30",
    "2026-1-1",
    "20261006",
    " 2026-10-06 ",
    "2026-10-06T00:00:00",
    "+2026-10-06",
    "-2026-10-06",
]
BAD_CHOICES = ["loan", "ASSET", "daily", "Monthly", "weekly", "ANNUAL"]
BAD_HORIZONS: list[Any] = [0, 51, -1, 2.5, 1.0, 10**400, 1e308]
HOSTILE_VALUES: list[Any] = [
    *WRONG_TYPES,
    *ODD_TEXT,
    *NUMBERS,
    *ODD_DATES,
    *BAD_CHOICES,
    *BAD_HORIZONS,
]
UNKNOWN_ARGUMENTS = ["unknown", "Name", "", "balance ", "horizon"]

TOOL_POOLS: dict[str, dict[str, list[Any]]] = {
    "set_account": {
        "name": ACCOUNT_NAMES,
        "kind": KINDS,
        "balance": AMOUNTS,
        "growth_rate": RATES,
        "volatility": RATES,
        "new_name": ACCOUNT_NAMES,
    },
    "remove_account": {"name": ACCOUNT_NAMES},
    "set_flow": {
        "name": FLOW_NAMES,
        "from": [*FLOW_ACCOUNT_NAMES, None],
        "to": FLOW_ACCOUNT_NAMES,
        "amount": AMOUNTS,
        "rate": RATES,
        "rate_of": FLOW_ACCOUNT_NAMES,
        "frequency": FREQUENCIES,
        "start_date": DATES,
        "end_date": [*DATES, None],
        "new_name": NEW_FLOW_NAMES,
    },
    "remove_flow": {"name": FLOW_NAMES},
    "set_inflation_rate": {"rate": RATES},
    "show_model": {},
    "project": {
        "horizon_years": HORIZONS,
        "granularity": GRANULARITIES,
        "in_todays_money": BOOLEANS,
    },
}
ALWAYS_BUILT_ARGUMENTS = {
    "set_account": {"name"},
    "remove_account": {"name"},
    "set_flow": {"name", "to", "frequency"},
    "remove_flow": {"name"},
    "set_inflation_rate": {"rate"},
}


async def succeed(client: Client, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, error_text(result)
    assert result.structured_content is not None
    return result.structured_content


async def fail(client: Client, tool: str, arguments: dict[str, Any]) -> str:
    result = await client.call_tool(tool, arguments)
    assert result.is_error, result.structured_content
    return error_text(result)


def error_text(result: CallToolResult) -> str:
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


async def what_if(client: Client, changes: list[dict[str, Any]], **options: Any) -> dict[str, Any]:
    return await succeed(client, "what_if", {"changes": changes, **options})


def build_arguments(generator: random.Random, tool: str) -> dict[str, Any]:
    always_built = ALWAYS_BUILT_ARGUMENTS.get(tool, set())
    arguments = {
        argument: generator.choice(pool)
        for argument, pool in TOOL_POOLS[tool].items()
        if argument in always_built or generator.random() < OPTIONAL_ARGUMENT_SHARE
    }
    if arguments and generator.random() < HOSTILE_SHARE:
        arguments[generator.choice(list(arguments))] = generator.choice(HOSTILE_VALUES)
    if generator.random() < UNKNOWN_ARGUMENT_SHARE:
        arguments[generator.choice(UNKNOWN_ARGUMENTS)] = generator.choice(HOSTILE_VALUES)
    return arguments


def describe(value: Any) -> str:
    if isinstance(value, str) and len(value) > SHOWN_TEXT_LENGTH:
        return f"<str of {len(value)} chars>"
    if isinstance(value, int) and abs(value) > SHOWN_INT_LIMIT:
        return f"<int of {len(str(abs(value)))} digits>"
    return repr(value)


def describe_call(tool: str, arguments: dict[str, Any]) -> str:
    shown = ", ".join(f"{name}={describe(value)}" for name, value in arguments.items())
    return f"{tool}({shown})"


async def find_protocol_error(client: Client, tool: str, arguments: dict[str, Any]) -> str | None:
    try:
        await client.call_tool(tool, arguments)
    except Exception as error:
        return f"{describe_call(tool, arguments)} raised {type(error).__name__}: {error}"
    return None
