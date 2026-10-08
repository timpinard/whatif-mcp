from collections.abc import Iterable
from typing import Any

from mcp import types

from whatif_mcp.core.model import Account, AccountKind
from whatif_mcp.core.money import round_money
from whatif_mcp.server.registry import EMPTY_INPUT_SCHEMA, RegisteredTool, ToolCall
from whatif_mcp.server.shaping import shape_account, shape_flow
from whatif_mcp.store import load_model, resolve_model_path

SHOW_MODEL_DESCRIPTION = (
    "Show the model: today, every account, every flow, the inflation rate, net worth today "
    "and the model file path."
)


def show_model(call: ToolCall) -> dict[str, Any]:
    path = resolve_model_path()
    model = load_model(path)
    return {
        "model_path": str(path),
        "today": call.today.isoformat(),
        "inflation_rate": model.inflation_rate,
        "net_worth_today": round_money(_net_worth(model.accounts)),
        "accounts": [shape_account(account) for account in model.accounts],
        "flows": [shape_flow(flow) for flow in model.flows],
    }


def _net_worth(accounts: Iterable[Account]) -> float:
    return sum(
        -account.balance if account.kind is AccountKind.LIABILITY else account.balance
        for account in accounts
    )


TOOLS = (
    RegisteredTool(
        types.Tool(
            name="show_model",
            description=SHOW_MODEL_DESCRIPTION,
            input_schema=EMPTY_INPUT_SCHEMA,
        ),
        show_model,
    ),
)
