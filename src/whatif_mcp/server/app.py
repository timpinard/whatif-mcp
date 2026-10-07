from collections.abc import Callable
from datetime import date
from typing import Any

from mcp.server.lowlevel import Server

SERVER_NAME = "whatif-mcp"


def create_server(today: Callable[[], date]) -> Server[Any]:
    return Server(SERVER_NAME)
