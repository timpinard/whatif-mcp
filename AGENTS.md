# AGENTS.md (CLAUDE.md is a symlink to this file)

## Project
whatif-mcp is an MCP server that answers "what if" questions about one person's finances. The
user describes accounts and recurring money flows through an AI assistant; the server projects
balances forward and compares a baseline against hypothetical changes. It runs locally over
stdio, keeps the model in a JSON file the user owns, and has no network or database dependency.
The projection behavior is ported from an existing engine (ADR 0004).

## Context docs (read before any task)
- docs/context/architecture.md
- docs/context/conventions.md
- docs/context/glossary.md
- docs/adr/ (accepted ADRs are binding)

## Commands
- Setup: `python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'`
- Gates (run all, in order): `scripts/gates.sh [docs/specs/NNNN-name.md]`
- Lint: `.venv/bin/ruff format --check . && .venv/bin/ruff check .`
- Typecheck: `.venv/bin/mypy src`
- Unit tests: `.venv/bin/pytest -m "not integration"`
- Integration tests: `.venv/bin/pytest -m integration`

## Rules
1. Work from a spec in docs/specs/. No spec, no code. Ask.
2. Do not change a spec to fit the code. Flag the conflict.
3. Run `scripts/gates.sh` before saying "done". Show the output.
4. One task = one PR. Keep diffs reviewable.
5. If an ADR blocks the approach, stop and report. Do not override.
6. Log regeneration count in the PR description.
7. Refer to docs by ID ("ADR NNNN", "Spec NNNN"), not by path. Only ADRs name external systems,
   repos, files or versions; everything else refers to the ADR. Accepted ADRs are never edited,
   only superseded, so a stale name in one is history, not rot.

## Non-goals for agents
- No dependency additions without an ADR.
- No schema migrations without explicit task.
