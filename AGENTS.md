# AGENTS.md (also symlink/copy as CLAUDE.md)

## Project
<one paragraph: what this system does, who uses it>

## Context docs (read before any task)
- docs/context/architecture.md
- docs/context/conventions.md
- docs/context/glossary.md
- docs/adr/ (accepted ADRs are binding)

## Commands
- Gates (run all, in order): `scripts/gates.sh`
- Lint: `<cmd>`
- Typecheck: `<cmd>`
- Unit tests: `<cmd>`
- Integration tests: `<cmd>`

## Rules
1. Work from a spec in docs/specs/. No spec, no code. Ask.
2. Do not change a spec to fit the code. Flag the conflict.
3. Run `scripts/gates.sh` before saying "done". Show the output.
4. One task = one PR. Keep diffs reviewable.
5. If an ADR blocks the approach, stop and report. Do not override.
6. Log regeneration count in the PR description.

## Non-goals for agents
- No dependency additions without an ADR.
- No schema migrations without explicit task.
