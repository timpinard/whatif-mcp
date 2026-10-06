# ADR 0005: uv for the development environment and lockfile
- Status: accepted
- Date: 2026-10-06
- Deciders: Timothy Pinard

## Context
ADR 0002 chose a plain venv with pip. Each task runs in a fresh agent session, so tool versions
can differ between tasks unless they are locked. MCP servers are commonly launched by end users
with `uvx`.

## Decision
Supersedes the development-environment line of ADR 0002; the rest of ADR 0002 stands.
- uv manages the environment, the Python version (`.python-version`: 3.12) and a committed
  `uv.lock`.
- Dev tools (pytest, ruff, mypy) are a `dev` dependency group, not an extra.
- Setup is `uv sync`; every gate runs through `uv run --locked`, which fails if `uv.lock` is out of
  date with `pyproject.toml`.
- The build backend stays hatchling. End users run the server with `uvx`.

## Consequences
- Every session gets the same tool versions; a dependency change shows up as a `uv.lock` diff.
- Developers need uv installed (0.12 or later).
- Adding a dependency still needs an ADR (ADR 0002); `uv add` is how it is then applied.

## Alternatives considered
- Plain venv and pip (ADR 0002): no lockfile, so versions drift between sessions.
- pip-tools for a lockfile: a second tool for what uv does in one.
