# ADR 0002: Python 3.12 with the official MCP SDK
- Status: accepted; development environment superseded by ADR 0005
- Date: 2026-10-06
- Deciders: Timothy Pinard

## Context
The projection math being ported (ADR 0004) is Python. The server must speak MCP over stdio and
install with one command into Claude Desktop or Claude Code.

## Decision
- Runtime: Python 3.12, package `whatif_mcp`, src layout, built with hatchling.
- Runtime dependency: `mcp` (the official Python SDK), and nothing else.
- Dev dependencies: `pytest`, `ruff`, `mypy`.
- Development uses a plain venv (`python3.12 -m venv`). End users may run it with `uvx` or `pipx`.

## Consequences
- The core stays dependency-free: no numpy. Monte Carlo runs in pure Python; its latency budget is
  set by the bands spec once measured, and missing it is the trigger to revisit numpy.
- Any further dependency needs its own ADR.

## Alternatives considered
- TypeScript MCP SDK: wider MCP ecosystem, but a rewrite of the math in a second language.
- numpy for Monte Carlo: faster, but a heavy install for a small tool; revisit only if the
  latency constraint is missed.
