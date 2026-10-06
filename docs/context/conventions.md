# Conventions
Owner's global engineering standards apply (scope discipline, comment rules, naming, ASCII-only
prose, anti-pattern list). This file adds what is specific to this repo.

## Code style
- Python 3.12, src layout (`src/whatif_mcp/`), `ruff format` and `ruff check`, `mypy --strict` on src.
- Dataclasses (frozen where possible) for domain types; no untyped dicts across module boundaries.
- Money is `float`, rounded to cents only when shaped for output.

## Naming
- Domain terms come from docs/context/glossary.md. Do not invent synonyms in code.
- MCP tool names are snake_case verbs: `set_account`, `project`, `what_if`.

## Error handling
- core raises typed exceptions (subclasses of `WhatIfError`); it never returns None as an error.
- server turns a `WhatIfError` into an MCP tool error whose message says what was wrong and
  which tool or argument fixes it.
- An ambiguous or unknown name is an error listing the candidates; never guess.

## Testing (what gets unit vs integration; naming: test_<AC-id>_<behavior> in tests/test_<spec-NNNN>_*.py)
- Unit: core and store, called directly. Fixed "today" in every test.
- Integration (`@pytest.mark.integration`): the server driven through an in-process MCP client
  session, against a model file in a temp directory.
- Parity: numbers ported from the source project are checked against expected values computed by the
  the source project engine for the same inputs, recorded as fixtures.

## Logging and observability
- `logging` to stderr only. No financial values or account names in logs above DEBUG.

## Branching and commits
- One branch per task: `task/NNNN-Tn-short-name`, cut from main. Merge to main only after the
  human merge gate.
- No remote. The "PR" is the branch plus `docs/reviews/NNNN-Tn.md` (gates output + review report).
- Author: Timothy Pinard <41369965+timpinard@users.noreply.github.com>. No Co-Authored-By trailers.
