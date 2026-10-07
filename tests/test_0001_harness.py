import pytest
from mcp import Client


@pytest.mark.anyio
@pytest.mark.integration
async def test_harness_session_initializes(client: Client) -> None:
    assert client.server_info is not None
    assert client.server_info.name == "whatif-mcp"
