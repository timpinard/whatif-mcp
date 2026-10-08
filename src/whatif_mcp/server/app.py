from collections.abc import Callable
from datetime import date
from typing import Any

from mcp.server.lowlevel import Server

from whatif_mcp.server.registry import create_registry_server
from whatif_mcp.server.tools import accounts, flows, project, read, what_if

SERVER_NAME = "whatif-mcp"

TOOLS = (*read.TOOLS, *accounts.TOOLS, *flows.TOOLS, *project.TOOLS, *what_if.TOOLS)


def create_server(today: Callable[[], date]) -> Server[Any]:
    return create_registry_server(SERVER_NAME, TOOLS, today)
