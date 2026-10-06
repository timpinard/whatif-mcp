# Plan 0001: Model and projection
- Spec: Spec 0001 (docs/specs/0001-model-and-projection.md)
- Status: draft
- Approved by:

## Approach
Build bottom-up along the dependency direction in docs/context/architecture.md: pure core first,
then the store, then the MCP tools, then the stdio process. Each layer is tested at the level
Spec 0001 assigns to its AC, so every task merges with gates green.

1. Skeleton and recurrence. Package, dev environment and gate tooling; core domain types
   (Model, Account, Flow, kinds, frequencies) and the `WhatIfError` hierarchy; occurrence
   generation (R9). A server factory with no tools yet, a stdio entry point, and the
   in-process MCP client fixture every integration test uses.
2. Core projection. One pure function from (model, today, horizon end, granularity) to a
   projection: monthly growth on the 1st, flow occurrences in model order, capped liability
   payments, rate flows read at the occurrence, period rows, per-account summary, per-flow
   totals, reaches_zero (R10 to R13). Event-driven by date (growth dates and occurrence dates
   merged and sorted), not a day-by-day loop, to keep R18 comfortable.
3. Store and read path. Model path resolution per call (R1), load with JSON and version
   checks, atomic 0600 write via temp file and `os.replace`, and `show_model` (R7).
4. Account tools. Name resolution (R8) shared by all tools; `set_account`, `remove_account`
   (R2, R3), with validation per R16.
5. Flow tools. `set_flow`, `remove_flow` (R4, R5), including null-clears, fixed/rate switching,
   `similar_flows`, and the one_time-never-fires check (R9).
6. Project tool. `project` arguments and shaping (R13, R14), today's money (R15),
   `set_inflation_rate` (R6), read-only tools never writing (R17), latency (R18).
7. Process hygiene. stdout carries only MCP messages; logging to stderr without names or
   amounts above DEBUG (R19).

Decisions taken here (the role file and templates are silent on them):
- "Today" reaches the server through the server factory as a callable returning a date; the
  stdio entry point passes the system clock, tests pass a fixed 2026-10-06. No environment
  variable for today: that would be a runtime input architecture.md does not list.
- The model path is resolved on every call (env var, else `~/.whatif/model.json` from HOME),
  so tests can set `WHATIF_MODEL_PATH` or HOME per test and AC1 holds.
- Editing operations (validate arguments, resolve names, apply to a model, describe
  `previous`) are pure functions over a core `Model` inside the server package, separate from
  the MCP handler wiring. The handler is load, call the operation, save, shape. This keeps
  architecture.md's split (validation and name resolution in server) and lets Spec 0002 apply
  the same operations to an in-memory copy without touching disk.
- The core projection takes a horizon end date, not a number of years, and exposes balances
  after the events of any date in range, so Spec 0003 (measure at by_date) can reuse it.
  Growth for one account on one date is computed in a single function, the natural seam for
  Spec 0004's per-year drawn rates. Neither seam is generalized now.
- Flows refer to accounts by name in the file and in memory; a rename rewrites the references
  in the same operation. An internal account id (useful for Spec 0002's identity matching) is
  left to the Spec 0002 plan rather than added unused now.
- MCP server API: Spec 0001 needs an argument literally named `from`, a distinction between an
  omitted argument and JSON null (R4), and error messages we write (R16). A decorator API that
  maps tools to Python function signatures cannot express the first two, so the plan uses the
  SDK's low-level server with hand-written input schemas and validation in our code. T1
  verifies this against the installed SDK and records the result in its review file.
- Async integration tests run on the anyio pytest plugin, which ships with anyio, already a
  dependency of the MCP SDK; no new dev dependency (ADR 0002).

## Components touched
All new; the repo has no code yet.
- Build and tooling: `pyproject.toml` (hatchling, runtime `mcp`, dev extra `pytest`, `ruff`,
  `mypy`; ruff, mypy strict and pytest config, `integration` marker registered with strict
  markers), console entry point.
- `whatif_mcp.core`: domain types and errors, recurrence, projection, today's-money deflation.
- `whatif_mcp.store`: path resolution, load, atomic save. Imports core types (architecture.md
  lists only server's arrows; store -> core is needed so no untyped dict crosses the boundary,
  and core still imports nothing from the other two).
- `whatif_mcp.server`: a package: server factory and tool registration, name resolution,
  account and flow operations, show_model and project shaping, stdio entry and logging setup.
- `tests/`: `conftest.py` (fixed today, temp model path, in-process session, Model W builders
  in core and file form) and the spec test files listed under Test strategy.

## Data / schema changes
Introduces the model file format version 1 exactly as in Spec 0001 (Interfaces and data
shapes). No existing data, so no migration. Key order in the written JSON follows the spec
example; flow order is the order flows were first added.

## ADR conformance (list ADRs checked)
- ADR 0001 (spec-driven): plan and tasks trace every AC of Spec 0001 to one task; no behavior
  beyond the spec. Conforms.
- ADR 0002 (Python 3.12, MCP SDK): Python 3.12, src layout, hatchling, runtime dependency `mcp`
  only, dev dependencies pytest, ruff, mypy only, plain venv. The anyio pytest plugin is used
  through the existing transitive dependency, not added. Conforms; reviewer to confirm
  `pyproject.toml` lists nothing else.
- ADR 0003 (JSON file): one file, env var override, atomic replace, 0600, `version`, never
  overwritten when unreadable. Conforms.
- ADR 0004 (port, do not share): core written fresh from Spec 0001, nothing imported or vendored
  from the source engine; expected numbers come from the spec's hand-checked AC. Conforms.
- No conflicts found.

## Risks and unknowns
- Kit gap, pytest exit code 5: `scripts/gates.sh` runs `pytest -m "not integration"` and
  `pytest -m integration` under `set -e`; pytest exits 5 when no test is selected (verified),
  so gates cannot pass until at least one unit and one integration test exist. T1 therefore
  ships a harness smoke test (`test_harness_session_initializes`) alongside its unit AC tests.
  It is the only test in the spec's files not named after an AC.
- Kit gap, AC coverage gate granularity: with the spec argument the gate requires every AC of
  the spec, so it fails on every task but the last. Tasks T1 to T6 run `scripts/gates.sh` with
  no argument (coverage stage skipped) plus a per-task grep for their own AC; T7 runs it with
  the spec. The implementer role says to always pass the spec; the task list overrides that for
  T1 to T6. See Tasks 0001.
- SDK unknowns (T1 verifies): whether the low-level server validates arguments against the
  input schema before our handler, and with what message. If its message does not name the
  argument (AC6 `balance="lots"`, AC9 `amount "lots"`), schema-level validation must be turned
  off or the schema kept permissive so our R16 messages reach the client. Also whether the
  SDK's own loggers emit tool arguments at INFO (R19, checked in T7).
- Environment: T1 needs network access for `pip install -e '.[dev]'`.
- AC24 is a wall-clock assertion (under 1 s); it can flake on a loaded machine. The projection
  is event-driven to keep a wide margin.
- Floating point: AC compare to the cent after many compounding steps (AC21 138437.49,
  10562.51). Internal values are never rounded between steps (spec); rounding only in shaping.
- T2 is the largest task (projection plus rows and summaries). If its non-test diff exceeds
  ~400 lines, split rows and summary (AC20, AC21) into a follow-up task rather than grow it.

Spec gaps (flagged for the owner, not fixed; the plan's working assumption in brackets):
1. How the log level is set is undefined; AC25 says "logging at INFO". [Default INFO on
   stderr, no knob. A knob would be a new runtime input and needs a spec change.]
2. A file that is valid JSON with `"version": 1` but the wrong shape (missing `accounts`, a
   flow without `frequency`, a string balance) is not covered by R1. [Same treatment as
   invalid JSON: every tool errors naming the path and the problem, file never overwritten.]
3. Allowed ranges for flow `amount` and `rate` are not stated the way growth_rate, volatility
   and inflation are. AC9 refuses amount 0, rate 0 and rate 1.5; negative amount, negative rate
   and rate exactly 1 are open. [amount > 0; 0 < rate <= 1.]
4. Rounding mode to cents is not stated (half-even vs half-up). [Half-up on the unrounded
   value; no current AC sits on a half cent as far as checked.]
5. Whether an integral float such as `horizon_years=5.0` counts as a whole number (AC22
   refuses 2.5). [Refused: JSON integer only.]
6. Whether `set_account` with a balance equal to the stored one moves balance_as_of. [Yes: a
   given balance always sets balance_as_of to today.]

## Test strategy (AC -> test level)
Levels are as the spec states; files are split by task so no two tasks edit the same test file.

| File | AC | Level | Task |
|------|----|-------|------|
| tests/test_0001_schedule.py | AC12, AC13 | unit | T1 |
| tests/test_0001_harness.py | (smoke, no AC) | integration | T1 |
| tests/test_0001_projection.py | AC14, AC15, AC16, AC17, AC18, AC19, AC20, AC21 | unit | T2 |
| tests/test_0001_store.py | AC3 | unit | T3 |
| tests/test_0001_show_model.py | AC11 | integration | T3 |
| tests/test_0001_accounts.py | AC4, AC5, AC6, AC7 | integration | T4 |
| tests/test_0001_flows.py | AC8, AC9, AC10 | integration | T5 |
| tests/test_0001_project_tool.py | AC1, AC2, AC22, AC23, AC24 | integration | T6 |
| tests/test_0001_stdio.py | AC25 | integration | T7 |

- Unit tests call core and store directly with today fixed at 2026-10-06.
- Integration tests use the in-process client session from `conftest.py` against a model file
  in a temp dir; a test that needs a starting model (Model W, AC7's extra accounts, AC24's 50
  accounts and flows) writes it through the store or as JSON, not through tools added in a
  later task.
- AC3 forces the failure by patching `os.replace` to raise.
- AC25 starts the server as a subprocess over stdio and speaks raw JSON-RPC lines so it can
  check every stdout line.
- Each AC appears in exactly one task.

## Rollout and rollback
Local only: no remote, no deploy. Each task is a branch `task/0001-Tn-short-name` merged to main
after the human merge gate; rollback is reverting that merge. Spec 0001 status moves to
implemented after T7 merges (owner, per docs/definition-of-done.md).
