from pathlib import Path

import pytest
from helpers import fail, what_if
from mcp import Client


def file_state(path: Path) -> tuple[bytes, int]:
    return path.read_bytes(), path.stat().st_mtime_ns


@pytest.mark.anyio
@pytest.mark.integration
async def test_AC8_what_if_never_writes(client: Client, model_w_file: Path) -> None:
    before = file_state(model_w_file)

    result = await what_if(
        client, [{"op": "set_flow", "name": "Salary", "amount": 3600}], horizon_years=1
    )

    assert result["persisted"] is False
    assert file_state(model_w_file) == before

    await fail(
        client,
        "what_if",
        {
            "changes": [
                {"op": "set_flow", "name": "Salary", "amount": 3600},
                {"op": "remove_flow", "name": "Yacht"},
            ]
        },
    )

    assert file_state(model_w_file) == before
