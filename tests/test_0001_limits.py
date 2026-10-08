import os
from collections.abc import Callable
from pathlib import Path

import pytest
from helpers import fail
from mcp import Client

NOT_UTF8_MODEL = b'{"version": 1, "x": "\xe9"}'
NESTING_DEPTH = 100_000
IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
READ_ONLY_CALLS = ("show_model", {})
WRITE_CALLS = ("set_inflation_rate", {"rate": 0.02})


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize("balance", [1_000_000_000_001, -1_000_000_000_001])
async def test_AC27_balance_beyond_a_trillion_is_refused(
    client: Client, model_path: Path, balance: int
) -> None:
    message = await fail(
        client, "set_account", {"name": "Big", "kind": "asset", "balance": balance}
    )

    assert message.startswith("balance ")
    assert "1,000,000,000,000" in message
    assert not model_path.exists()


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC27_flow_amount_beyond_a_trillion_is_refused(
    client: Client, model_w_file: Path
) -> None:
    before = model_w_file.read_bytes()

    message = await fail(
        client,
        "set_flow",
        {"name": "Huge", "to": "Checking", "amount": 1_000_000_000_001, "frequency": "monthly"},
    )

    assert message.startswith("amount ")
    assert "1,000,000,000,000" in message
    assert model_w_file.read_bytes() == before


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC27_projection_too_large_to_report_names_horizon_years(
    client: Client, model_path: Path
) -> None:
    model_path.write_text(
        '{"version": 1, "inflation_rate": 0.03, "accounts": [{"name": "Debt", '
        '"kind": "liability", "balance": 1000000, "balance_as_of": "2026-10-06", '
        '"growth_rate": 1.0, "volatility": 0}], "flows": []}'
    )
    before = model_path.read_bytes()

    message = await fail(client, "project", {"horizon_years": 50})

    assert "horizon_years" in message
    assert "growth_rate" in message
    assert "inflation" in message
    assert model_path.read_bytes() == before


@pytest.mark.anyio
@pytest.mark.integration
async def test_R14_todays_money_too_large_to_report_names_horizon_years(
    client: Client, model_path: Path
) -> None:
    model_path.write_text(
        '{"version": 1, "inflation_rate": -0.75, "accounts": [{"name": "Cash", '
        '"kind": "asset", "balance": 1000, "balance_as_of": "2026-10-06", '
        '"growth_rate": 0, "volatility": 0}], "flows": []}'
    )
    before = model_path.read_bytes()

    # 1000 / 0.25^50 is about 1.3e33, above 1e15
    message = await fail(client, "project", {"horizon_years": 50, "in_todays_money": True})

    assert "horizon_years" in message
    assert "inflation" in message
    assert model_path.read_bytes() == before


@pytest.mark.anyio
@pytest.mark.integration
async def test_R14_file_balances_near_the_float_limit_are_a_tool_error(
    client: Client, model_path: Path
) -> None:
    model_path.write_text(
        '{"version": 1, "inflation_rate": 0.03, "accounts": ['
        '{"name": "A", "kind": "asset", "balance": 1e308, "balance_as_of": "2026-10-06", '
        '"growth_rate": 0, "volatility": 0}, '
        '{"name": "B", "kind": "asset", "balance": 1e308, "balance_as_of": "2026-10-06", '
        '"growth_rate": 0, "volatility": 0}], "flows": []}'
    )
    before = model_path.read_bytes()

    for tool in ("project", "show_model"):
        message = await fail(client, tool, {})

        assert str(model_path) in message
        assert "balance" in message
    assert model_path.read_bytes() == before


def write_not_utf8(path: Path) -> None:
    path.write_bytes(NOT_UTF8_MODEL)


def write_unreadable(path: Path) -> None:
    path.write_text('{"version": 1, "inflation_rate": 0.03, "accounts": [], "flows": []}')
    path.chmod(0)


def make_directory(path: Path) -> None:
    path.mkdir()


def snapshot(path: Path) -> tuple[bool, bytes | None]:
    if path.is_dir():
        return True, None
    original_mode = path.stat().st_mode
    path.chmod(0o600)
    content = path.read_bytes()
    path.chmod(original_mode)
    return False, content


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.parametrize(
    "make_model_path",
    [
        write_not_utf8,
        pytest.param(
            write_unreadable,
            marks=pytest.mark.skipif(IS_ROOT, reason="root reads a mode 000 file anyway"),
        ),
        make_directory,
    ],
)
async def test_AC28_unreadable_model_file_is_a_tool_error_naming_the_path(
    client: Client, model_path: Path, make_model_path: Callable[[Path], None]
) -> None:
    make_model_path(model_path)
    before = snapshot(model_path)

    for tool, arguments in (READ_ONLY_CALLS, WRITE_CALLS):
        message = await fail(client, tool, arguments)

        assert str(model_path) in message
        assert snapshot(model_path) == before


@pytest.mark.anyio
@pytest.mark.integration
async def test_R1_nesting_too_deep_to_parse_is_not_valid_json(
    client: Client, model_path: Path
) -> None:
    model_path.write_text('{"version": 1, "x": ' + "[" * NESTING_DEPTH + "]" * NESTING_DEPTH + "}")
    before = model_path.read_bytes()

    for tool, arguments in (READ_ONLY_CALLS, WRITE_CALLS):
        message = await fail(client, tool, arguments)

        assert str(model_path) in message
        assert "not valid JSON" in message
    assert model_path.read_bytes() == before


@pytest.mark.anyio
@pytest.mark.integration
async def test_R1_not_utf8_bytes_are_not_valid_json(client: Client, model_path: Path) -> None:
    write_not_utf8(model_path)

    message = await fail(client, *READ_ONLY_CALLS)

    assert "not valid JSON" in message


@pytest.mark.anyio
@pytest.mark.integration
async def test_R1_a_file_as_parent_directory_is_a_tool_error_naming_the_path(
    client: Client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"
    parent.write_text("x")
    path = parent / "model.json"
    monkeypatch.setenv("WHATIF_MODEL_PATH", str(path))

    for tool, arguments in (READ_ONLY_CALLS, WRITE_CALLS):
        message = await fail(client, tool, arguments)

        assert str(path) in message
    assert parent.read_text() == "x"
