# AGENTS.md (CLAUDE.md is a symlink to this file)

## Project
whatif-mcp is an MCP server that answers "what if" questions about one person's finances. The
user describes accounts and recurring money flows through an AI assistant; the server projects
balances forward and compares a baseline against hypothetical changes. It runs locally over
stdio, keeps the model in a JSON file the user owns, and has no network or database dependency.
The projection behavior is ported from an existing engine (ADR 0004).

## Process
Spec-driven, with the sdd-kit plugin (version in `.sdd-kit`). Stages: epic -> spec -> plan -> build
-> merge, each started with its skill (`/sdd-kit:epic`, `/sdd-kit:spec`, `/sdd-kit:plan`,
`/sdd-kit:build`). Human gates: accept ADRs, approve epic, approve spec (QA signs off the AC), approve plan, merge,
QA findings (bug or spec gap).

## Read before any task
- docs/context/architecture.md, docs/context/conventions.md, docs/context/glossary.md
- docs/adr/ (accepted ADRs are binding)

## Commands
- Setup: `uv sync` (ADR 0005), and `claude plugin marketplace add <path to sdd-kit>` (the kit has no git remote)
- Gates: `scripts/gates.sh [docs/specs/NNNN-name.md [AC ids...]]`
- Lint: `uv run --locked ruff format --check .` then `uv run --locked ruff check .`
- Typecheck: `uv run --locked mypy src`
- Unit tests: `uv run --locked pytest -m "not integration"`
- Integration tests: `uv run --locked pytest -m integration`

## Rules
1. No spec, no code. Ask.
2. A spec is changed only by its owner. Code that disagrees with a spec is flagged, not reconciled.
3. "Done" means `scripts/gates.sh` green, with the output shown.
4. An ADR that blocks the approach stops the work; report it.
5. Refer to docs by ID; only ADRs name external systems (skill `domain-docs`).
6. Every runtime or dev dependency needs an ADR first.
7. Problems with the process itself go in docs/kit-feedback.md.
