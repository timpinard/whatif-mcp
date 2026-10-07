import json
import queue
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

SERVER_COMMAND = str(Path(sys.executable).with_name("whatif-mcp"))
PROTOCOL_VERSION = "2026-07-28"
EXIT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 10
JSONRPC_VERSION = "2.0"
END_OF_STDOUT = ""
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
        self._unread_lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._read_stdout, daemon=True).start()

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self._unread_lines.put(line)
        self._unread_lines.put(END_OF_STDOUT)

    def read_line(self) -> str:
        line = self._unread_lines.get(timeout=READ_TIMEOUT_SECONDS)
        if line != END_OF_STDOUT:
            self.stdout_lines.append(line)
        return line

    def send(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps({"jsonrpc": JSONRPC_VERSION, **message}) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self.send({"id": request_id, "method": method, "params": params})
        while True:
            line = self.read_line()
            assert line != END_OF_STDOUT, "server closed stdout before answering"
            message: dict[str, Any] = json.loads(line)
            if message.get("id") == request_id:
                return message

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = self.request("tools/call", {"name": name, "arguments": arguments})[
            "result"
        ]
        return result

    def close(self) -> None:
        assert self.process.stdin is not None
        self.process.stdin.close()
        self.process.wait(timeout=EXIT_TIMEOUT_SECONDS)
        while self.read_line() != END_OF_STDOUT:
            pass


@contextmanager
def running_server(stderr_path: Path) -> Iterator[StdioSession]:
    with stderr_path.open("w") as stderr:
        process = subprocess.Popen(
            [SERVER_COMMAND],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
        )
    try:
        yield StdioSession(process)
    finally:
        process.kill()
        process.wait()


@pytest.mark.integration
def test_AC25_stdout_is_mcp_only_and_logs_carry_no_financial_values(
    model_path: Path, tmp_path: Path
) -> None:
    stderr_path = tmp_path / "stderr.log"
    with running_server(stderr_path) as session:
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
        session.close()

    for line in session.stdout_lines:
        assert json.loads(line)["jsonrpc"] == JSONRPC_VERSION, line
    stderr = stderr_path.read_text()
    for value in FINANCIAL_VALUES:
        assert value not in stderr


LOGGING_PROBE_MESSAGE = "logging probe record"
LOGGING_PROBE = (
    "import logging\n"
    "from whatif_mcp.server.stdio import configure_logging\n"
    "configure_logging()\n"
    f"logging.getLogger('whatif_mcp').info({LOGGING_PROBE_MESSAGE!r})\n"
)


@pytest.mark.integration
def test_R19_entry_point_logs_info_to_stderr_not_stdout() -> None:
    completed = subprocess.run(
        [sys.executable, "-c", LOGGING_PROBE],
        capture_output=True,
        text=True,
        timeout=EXIT_TIMEOUT_SECONDS,
    )

    assert LOGGING_PROBE_MESSAGE in completed.stderr
    assert LOGGING_PROBE_MESSAGE not in completed.stdout
