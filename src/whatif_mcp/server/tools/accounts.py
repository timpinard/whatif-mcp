from typing import Any

from mcp import types

from whatif_mcp.server.operations import accounts as operations
from whatif_mcp.server.registry import RegisteredTool, ToolCall
from whatif_mcp.server.shaping import shape_account
from whatif_mcp.server.tools.writing import write_model_file
from whatif_mcp.store import load_model, resolve_model_path

SET_ACCOUNT_DESCRIPTION = (
    "Create an account, or update only the given fields of an existing one (names match "
    "ignoring case and surrounding spaces). kind and balance are required for a new account. "
    "Liability balances are amounts owed. Rates are decimals: 0.07 means 7%."
)
REMOVE_ACCOUNT_DESCRIPTION = "Remove an account that no flow uses."

NAME_PROPERTY = {"type": "string", "description": "Account name."}

SET_ACCOUNT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": NAME_PROPERTY,
        "kind": {"type": "string", "enum": ["asset", "liability"]},
        "balance": {"type": "number", "description": "Balance today; for a liability, owed."},
        "growth_rate": {
            "type": "number",
            "description": "Annual rate: effective return for an asset, APR for a liability.",
        },
        "volatility": {"type": "number", "description": "Yearly standard deviation, 0 to 1."},
        "new_name": {"type": "string", "description": "Rename the account."},
    },
    "required": ["name"],
    "additionalProperties": False,
}
REMOVE_ACCOUNT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"name": NAME_PROPERTY},
    "required": ["name"],
    "additionalProperties": False,
}


def set_account(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    edit = operations.set_account(load_model(path), call.arguments, call.today)
    write_model_file(path, edit.model)
    account = shape_account(edit.account)
    if edit.previous is None:
        return {"created": True, "account": account}
    earlier = shape_account(edit.previous)
    previous = {key: value for key, value in earlier.items() if account[key] != value}
    return {"created": False, "account": account, "previous": previous}


def remove_account(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    removal = operations.remove_account(load_model(path), call.arguments)
    write_model_file(path, removal.model)
    return {"removed": shape_account(removal.account)}


TOOLS = (
    RegisteredTool(
        types.Tool(
            name="set_account",
            description=SET_ACCOUNT_DESCRIPTION,
            input_schema=SET_ACCOUNT_SCHEMA,
        ),
        set_account,
    ),
    RegisteredTool(
        types.Tool(
            name="remove_account",
            description=REMOVE_ACCOUNT_DESCRIPTION,
            input_schema=REMOVE_ACCOUNT_SCHEMA,
        ),
        remove_account,
    ),
)
