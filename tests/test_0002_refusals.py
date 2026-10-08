from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from helpers import fail
from mcp import Client

from whatif_mcp.core.model import Model

PAY_CUT = {"op": "set_flow", "name": "Salary", "amount": 3600}


def file_state(path: Path) -> tuple[bytes, int]:
    return path.read_bytes(), path.stat().st_mtime_ns


async def refuse(client: Client, changes: Any) -> str:
    return await fail(client, "what_if", {"changes": changes})


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC7_failing_change_named_by_position(client: Client, model_w_file: Path) -> None:
    message = await refuse(client, [PAY_CUT, {"op": "remove_flow", "name": "Yacht"}])

    assert "change 2" in message
    assert "Yacht" in message
    assert "Salary, Car payment" in message

    message = await refuse(client, [{"op": "set_account", "name": "Savings", "growth_rate": 7}])

    assert "change 1" in message
    assert "0.07" in message


OPS_LISTED = "set_account, remove_account, set_flow, remove_flow"
REMOVE_EVERYTHING = [
    {"op": "remove_flow", "name": "Salary"},
    {"op": "remove_flow", "name": "Car payment"},
    {"op": "remove_account", "name": "Checking"},
    {"op": "remove_account", "name": "Savings"},
    {"op": "remove_account", "name": "Car loan"},
]


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC9_invalid_change_lists_refused(
    client: Client, model_w_file: Path, write_model_file: Callable[[Model], Path]
) -> None:
    assert "changes" in await refuse(client, [])

    message = await refuse(client, [{"op": "rename", "name": "Salary"}])
    assert "change 1" in message
    assert OPS_LISTED in message

    for malformed in ["Salary", {"name": "Salary"}, {"op": 5}]:
        message = await refuse(client, [PAY_CUT, malformed])
        assert "change 2" in message
        assert "op" in message

    assert "hypothetical model has no accounts" in await refuse(client, REMOVE_EVERYTHING)

    empty_model_file = write_model_file(Model())
    before = file_state(empty_model_file)
    project_message = await fail(client, "project", {})

    message = await refuse(
        client, [{"op": "set_account", "name": "Checking", "kind": "asset", "balance": 1000}]
    )

    assert message == project_message
    assert "set_account" in message
    assert file_state(empty_model_file) == before


@pytest.mark.anyio
@pytest.mark.integration
async def test_R6_missing_or_non_list_changes_refused(client: Client, model_w_file: Path) -> None:
    assert "changes" in await fail(client, "what_if", {})
    for changes in ["Salary", {"op": "set_flow"}, 5, None]:
        assert "changes" in await refuse(client, changes)


@pytest.mark.anyio
@pytest.mark.integration
async def test_R6_change_that_is_not_an_object_refused(client: Client, model_w_file: Path) -> None:
    for malformed in [5, None, True, ["op"], []]:
        message = await refuse(client, [PAY_CUT, malformed])
        assert "change 2" in message
        assert "object" in message


@pytest.mark.anyio
@pytest.mark.integration
async def test_R6_op_missing_or_not_a_known_text_refused(client: Client, model_w_file: Path) -> None:
    for malformed in [{}, {"op": None}, {"op": ["set_flow"]}, {"op": {}}, {"op": "Set_Flow"}]:
        message = await refuse(client, [PAY_CUT, malformed])
        assert "change 2" in message
        assert OPS_LISTED in message


@pytest.mark.anyio
@pytest.mark.integration
async def test_R6_unknown_key_in_change_refused_as_the_tool_would(
    client: Client, model_w_file: Path
) -> None:
    tool_message = await fail(client, "remove_flow", {"name": "Salary", "amount": 1})

    message = await refuse(client, [PAY_CUT, {"op": "remove_flow", "name": "Salary", "amount": 1}])

    assert message == f"change 2: {tool_message}"


@pytest.mark.anyio
@pytest.mark.integration
async def test_R6_baseline_without_accounts_checked_before_any_change(
    client: Client, write_model_file: Callable[[Model], Path]
) -> None:
    write_model_file(Model())
    project_message = await fail(client, "project", {})

    message = await refuse(client, [{"op": "remove_account", "name": "Checking"}])

    assert message == project_message
