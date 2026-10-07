import asyncio
from datetime import date

from mcp.server.stdio import stdio_server

from whatif_mcp.server.app import create_server


async def _serve() -> None:
    server = create_server(date.today)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_serve())
