from collections.abc import AsyncIterator, Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model
from whatif_mcp.server import create_server
from whatif_mcp.store import save_model

FIXED_TODAY = date(2026, 10, 6)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def today() -> date:
    return FIXED_TODAY


@pytest.fixture
def model_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "model.json"
    monkeypatch.setenv("WHATIF_MODEL_PATH", str(path))
    return path


@pytest.fixture
async def client(model_path: Path, today: date) -> AsyncIterator[Client]:
    async with Client(create_server(lambda: today)) as session:
        yield session


@pytest.fixture
def model_w(today: date) -> Model:
    return Model(
        accounts=(
            Account("Checking", AccountKind.ASSET, 5000.0, today),
            Account("Savings", AccountKind.ASSET, 0.0, today),
            Account("Car loan", AccountKind.LIABILITY, 10000.0, today, growth_rate=0.06),
        ),
        flows=(
            Flow(
                "Salary", None, "Checking", 4000.0, None, None, Frequency.MONTHLY, date(2026, 11, 1)
            ),
            Flow(
                "Car payment",
                "Checking",
                "Car loan",
                500.0,
                None,
                None,
                Frequency.MONTHLY,
                date(2026, 11, 1),
            ),
        ),
    )


@pytest.fixture
def write_model_file(model_path: Path) -> Callable[[Model], Path]:
    def write(model: Model) -> Path:
        save_model(model_path, model)
        return model_path

    return write


@pytest.fixture
def model_w_file(write_model_file: Callable[[Model], Path], model_w: Model) -> Path:
    return write_model_file(model_w)


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
