# Conventions
Owner's global engineering standards apply (scope discipline, comment rules, naming, ASCII-only
prose, anti-pattern list). This file adds what is specific to this repo.

## Code style
- Python 3.12, src layout (`src/whatif_mcp/`), `ruff format` and `ruff check`, `mypy --strict` on src.
- Dataclasses (frozen where possible) for domain types; no untyped dicts across module boundaries.
- Exception: a tool's JSON result may be a `dict[str, Any]` from the tool module to the MCP
  registry; domain data stays typed (owner ruling, Task 0001-T3 review).
- Money is `float`, rounded to cents only when shaped for output.

## Numbers and precision
- Money is `float` internally and never rounded between steps.
- Output money is rounded to cents, half up, on the unrounded value (Spec 0001, Interfaces).
- Derived values (differences, totals) are computed before rounding, not from rounded figures.
- Tests compare money to the cent.

## Naming
- Domain terms come from docs/context/glossary.md. Do not invent synonyms in code.
- MCP tool names are snake_case verbs: `set_account`, `project`, `what_if`.

## Error handling
- core raises typed exceptions (subclasses of `WhatIfError`); it never returns None as an error.
- server turns a `WhatIfError` into an MCP tool error whose message says what was wrong and
  which tool or argument fixes it.
- An ambiguous or unknown name is an error listing the candidates; never guess.

## Testing (naming: test_<AC-id>_<behavior> in tests/test_<spec-NNNN>_*.py)
- Behavior a requirement states and no AC covers: `test_R<n>_<behavior>` (owner ruling, Task
  0001-T3 review).
- Seams: core functions (unit), the store against a temp file (unit), MCP tools through an
  in-process client session (integration), the server as a subprocess over stdio (integration).
  Each plan names the seam per AC.
- Unit: core and store, called directly. Fixed "today" in every test.
- Integration (`@pytest.mark.integration`): the server driven through an in-process MCP client
  session, or run as a subprocess over stdio, against a model file in a temp directory.
- Expected numbers are hand-checked and the arithmetic is shown in a one-line comment or the AC.

## Logging and observability
- `logging` to stderr only. No financial values or account names in logs above DEBUG.

## Branching and commits
- One branch per task: `task/NNNN-Tn-short-name`, cut from the integration branch (AGENTS.md) and
  merged into it at the human merge gate. From Spec 0002 the integration branch is
  `spec/NNNN-name`, merged to main at the owner gate after the spec's full gate passes.
- No remote. The "PR" is the branch plus `docs/reviews/NNNN-Tn.md` (gates output + review report).
- Author: Timothy Pinard <41369965+timpinard@users.noreply.github.com>. No Co-Authored-By trailers.
