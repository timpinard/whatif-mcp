from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from mcp import Client

from whatif_mcp.core.model import Account, AccountKind, Flow, Frequency, Model
from whatif_mcp.server import create_server

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
