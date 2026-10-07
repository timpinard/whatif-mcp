from collections.abc import Callable
from datetime import date
from typing import Any

from mcp.server.lowlevel import Server

from whatif_mcp.server.registry import create_registry_server
from whatif_mcp.server.tools import accounts, project, read

SERVER_NAME = "whatif-mcp"

TOOLS = (*read.TOOLS, *accounts.TOOLS, *project.TOOLS)


def create_server(today: Callable[[], date]) -> Server[Any]:
    return create_registry_server(SERVER_NAME, TOOLS, today)
