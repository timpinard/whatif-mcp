import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SERVER_COMMAND = str(Path(sys.executable).with_name("whatif-mcp"))
PROTOCOL_VERSION = "2026-07-28"
EXIT_TIMEOUT_SECONDS = 10
FINANCIAL_VALUES = ("Checking", "Salary", "Car loan", "4000")

MODEL_W_CALLS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("set_account", {"name": "Checking", "kind": "asset", "balance": 5000}),
    ("set_account", {"name": "Savings", "kind": "asset", "balance": 0}),
    (
        "set_account",
        {"name": "Car loan", "kind": "liability", "balance": 10000, "growth_rate": 0.06},
    ),
    (
        "set_flow",
        {
            "name": "Salary",
            "to": "Checking",
            "amount": 4000,
            "frequency": "monthly",
            "start_date": "2026-11-01",
        },
    ),
    (
        "set_flow",
        {
            "name": "Car payment",
            "from": "Checking",
            "to": "Car loan",
            "amount": 500,
            "frequency": "monthly",
            "start_date": "2026-11-01",
        },
    ),
)


class StdioSession:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self.process = process
        self.stdout_lines: list[str] = []
        self.next_id = 1

    def send(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self.send({"id": request_id, "method": method, "params": params})
        assert self.process.stdout is not None
        while True:
            line = self.process.stdout.readline()
            assert line, "server closed stdout before answering"
            self.stdout_lines.append(line)
            message: dict[str, Any] = json.loads(line)
            if message.get("id") == request_id:
                return message

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = self.request("tools/call", {"name": name, "arguments": arguments})[
            "result"
        ]
        return result


@pytest.mark.integration
def test_AC25_stdout_is_mcp_only_and_logs_carry_no_financial_values(model_path: Path) -> None:
    process = subprocess.Popen(
        [SERVER_COMMAND],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    session = StdioSession(process)
    session.request(
        "initialize",
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    )
    session.send({"method": "notifications/initialized"})
    for tool, arguments in MODEL_W_CALLS:
        assert not session.call_tool(tool, arguments)["isError"]
    assert not session.call_tool("show_model", {})["isError"]
    assert not session.call_tool("project", {})["isError"]
    assert session.call_tool("set_flow", {"name": "Salry", "amount": 4100})["isError"]

    remaining_stdout, stderr = process.communicate(timeout=EXIT_TIMEOUT_SECONDS)
    stdout_lines = session.stdout_lines + remaining_stdout.splitlines(keepends=True)

    for line in stdout_lines:
        assert json.loads(line)["jsonrpc"] == "2.0", line
    for value in FINANCIAL_VALUES:
        assert value not in stderr
