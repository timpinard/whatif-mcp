import random
from collections.abc import Callable
from pathlib import Path

import pytest
from helpers import TOOL_POOLS, build_arguments, find_protocol_error
from mcp import Client

from whatif_mcp.core.model import Model

SEED = 20261008
CALL_COUNT = 600
RESET_EVERY = 50


@pytest.mark.anyio
@pytest.mark.integration
async def test_R16_no_tool_returns_an_internal_error(
    client: Client,
    model_w_file: Path,
    model_w: Model,
    write_model_file: Callable[[Model], Path],
) -> None:
    generator = random.Random(SEED)
    failures: list[str] = []

    for call_number in range(CALL_COUNT):
        if call_number % RESET_EVERY == 0:
            write_model_file(model_w)
        tool = generator.choice(list(TOOL_POOLS))
        failure = await find_protocol_error(client, tool, build_arguments(generator, tool))
        if failure is not None:
            failures.append(failure)

    assert not failures, "\n".join(failures)
