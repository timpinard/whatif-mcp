# Plan 0001: Model and projection
- Spec: Spec 0001
- Status: approved
- Approved by: Timothy Pinard, 2026-10-07
- Jira:
- History: first approved 2026-10-06 (Timothy Pinard) as layer tasks under sdd-kit 0.1; Task
  0001-T1 merged under it. T2 to T7 re-planned as slices under sdd-kit 0.2.2 on 2026-10-07.

## Approach
Task 0001-T1 (merged) built the package, gates, core types, recurrence (AC12, AC13), an empty
server factory, the stdio entry point and the in-process client fixture. The rest is six slices,
each a path through the layers it needs (Tasks 0001):

- T2 core projection and T3 read path run in parallel: neither touches the other's modules.
- T4 accounts, then T5 project and T6 flows in parallel, then T7 process hygiene.

T2 is the one layer-only slice. Reason: the spec places all of AC14 to AC21 at the core seam
(S1), no tool AC can land before T3's store and dispatch exist, and keeping it core-only lets it
run beside T3.

Decisions carried from the first approval:
- "Today" reaches the server through the server factory as a callable returning a date; the
  stdio entry point passes the system clock, tests pass a fixed 2026-10-06. No environment
  variable for today: architecture.md lists no such runtime input.
- The model path is resolved on every call (env var, else `~/.whatif/model.json` from HOME), so
  tests set `WHATIF_MODEL_PATH` or HOME per test and AC1 holds.
- Editing operations (validate arguments, resolve names, apply to a model, describe `previous`)
  are pure functions over a core `Model` inside the server package, separate from the MCP
  handler wiring. A handler is load, call the operation, save, shape. Spec 0002 applies the
  same operations to an in-memory copy without touching disk.
- The core projection takes a horizon end date, not a number of years, and exposes balances
  after the events of any date in range, so Spec 0003 (measure at by_date) can reuse it. Growth
  for one account on one date is computed in a single function, the seam for Spec 0004's
  per-year drawn rates. Neither seam is generalized now.
- Flows refer to accounts by name in the file and in memory; a rename rewrites the references in
  the same operation. An internal account id is left to the Spec 0002 plan.
- The SDK's low-level server with hand-written input schemas; validation and every R16 message
  are ours. Task 0001-T1 verified that the SDK does not validate input schemas, passes `from`
  through unchanged and distinguishes omitted from null (its review record).
- Async integration tests run on the anyio pytest plugin, which ships with anyio, already a
  dependency of the MCP SDK.

Decisions taken in this re-plan:
- Projection is event-driven by date (growth dates and occurrence dates merged and sorted), not
  a day-by-day loop, to keep R18 comfortable.
- T3 sets up tool registration as one module per tool group (read, accounts, flows, project),
  each exporting its tool definitions and handlers; `app.py` only concatenates them. T5 and T6
  then merge without conflicting.
- Money is rounded to cents, half up, in one shaping helper created in T3 and used by every
  tool result.

## Seams (where tests observe behavior; agreed with the owner)
Agreed 2026-10-07 by Timothy Pinard (engineer); QA review of what each seam misses: Timothy
Pinard.

| Seam | What it catches | What it misses |
|------|-----------------|----------------|
| S1 core functions (unit): `occurrence_dates`, the projection `(model, today, horizon_end, granularity) -> Projection` with unrounded floats, today's-money deflation. AC12 to AC21 | All projection math: occurrence filtering, growth, caps, same-day order, period boundaries, totals, reaches_zero | Rounding and result key names; argument validation; the file |
| S2 store against a temp file (unit): load and save. AC3 | A failed final replace leaves the previous bytes | Mode 0600, directory creation, path resolution, error text reaching the client (S3 covers these via AC1, AC2); a crash during the temp-file write (only `os.replace` failure is simulated); a leftover temp file (not specified) |
| S3 MCP tools through the in-process client (integration). AC1, AC2, AC4 to AC11, AC22 to AC24, AC26 | Validation messages, `isError`, name resolution, rounding and shape, file bytes unchanged, read-only tools, latency including dispatch | stdio framing, stdout pollution, logging setup, the real clock |
| S4 server as a subprocess over stdio (integration). AC25 | Anything on stdout from our code or the SDK; log content at INFO; the console entry point starts | DEBUG logs (by design). The AC25 test also makes one rejected call (an unknown flow name, whose error lists names), so error-path logging is seen; its assertions stay the AC's |

Not observed by any seam, checked by review (see Risks): today read from the clock once per call;
"never overwritten when unreadable" for write tools other than `set_account`.

## Components touched
- `whatif_mcp.core`: projection (T2), today's-money deflation (T5). Existing types and
  recurrence unchanged.
- `whatif_mcp.store`: new (T3). Path resolution, load with JSON, version and shape checks,
  atomic 0600 save. Imports core types; core imports nothing from it.
- `whatif_mcp.server`: tool registry and dispatch, error mapping, money shaping, `show_model`
  (T3); name resolution and account operations (T4); `project` and `set_inflation_rate` (T5);
  flow operations (T6); logging setup in the stdio entry point (T7).
- `tests/`: per Test layout.

## Data / schema changes
Introduces the model file format version 1 exactly as in Spec 0001 (Interfaces and data shapes).
No existing data, so no migration. Key order in the written JSON follows the spec example; flow
order is the order flows were first added.

## ADR conformance (list ADRs checked)
- ADR 0001: every AC of Spec 0001 lands in exactly one task; nothing beyond the spec. Conforms.
- ADR 0002: Python 3.12, `mcp` the only runtime dependency, no new dev dependency. Conforms.
- ADR 0003: one file, env var override, atomic replace, 0600, `version`, never overwritten when
  unreadable. Conforms.
- ADR 0004: core written from Spec 0001; expected numbers are the spec's hand-checked AC.
  Conforms.
- ADR 0005: gates through `uv run --locked`. Conforms.
- No conflicts found.

## Risks and unknowns
- T2 is the largest slice (~260 non-test lines estimated). If it passes ~400, AC15 (rate flows)
  and AC21 (Model W summary) move to a T2b that blocks T5.
- AC24 is a wall-clock assertion (under 1 s) and can flake on a loaded machine; the event-driven
  projection keeps a wide margin.
- Floating point: AC compare to the cent after many compounding steps (AC21 138437.49,
  10562.51). Internal values are never rounded between steps; rounding only in shaping.
- Whether the SDK's own loggers emit tool arguments at INFO (R19) is unknown until T7.
- Review-only checks (no seam observes them): the stdio entry point passes the clock, not a
  fixed date; every write tool loads through the same guarded path as `set_account`, so an
  unreadable file is never overwritten.
- T2 and T3 both add builders to `tests/conftest.py`; the second to merge rebases it.

## Spec gaps (flagged for the owner; working assumption in brackets; resolved by amending the spec)
Resolved by the owner on 2026-10-07 and amended into Spec 0001:
1. Validation on flow update. [The resulting flow must satisfy every create rule; the one_time
   never-fires check runs only when start_date or frequency is given.] R4.
2. Changing an account's kind. [Allowed; the resulting account is validated as a new one.] R2.
3. `rate_of` without `rate`. [Error naming `rate`, unless the flow is already a rate flow, where
   it retargets.] R4.
4. Half-up rounding was observed by no AC. [New AC26 on a 0.125 balance.] AC26.

Earlier gaps (2026-10-06 amendment) stand as amended.

## Test layout (test files, which task owns each, shared fixtures)
| File | AC | Seam | Task |
|------|----|------|------|
| tests/test_0001_schedule.py | AC12, AC13 | S1 | T1 (done) |
| tests/test_0001_harness.py | (smoke, no AC) | S3 | T1 (done) |
| tests/test_0001_projection.py | AC14 to AC21 | S1 | T2 |
| tests/test_0001_store.py | AC3 | S2 | T3 |
| tests/test_0001_show_model.py | AC11, AC26 | S3 | T3 |
| tests/test_0001_accounts.py | AC4, AC5, AC6, AC7 | S3 | T4 |
| tests/test_0001_project_tool.py | AC1, AC2, AC22, AC23, AC24 | S3 | T5 |
| tests/test_0001_flows.py | AC8, AC9, AC10 | S3 | T6 |
| tests/test_0001_stdio.py | AC25 | S4 | T7 |

Shared fixtures in `tests/conftest.py`: fixed today, temp model path and in-process client
(T1); Model W in core form (T2); writing a model file through the store, Model W in file form
(T3). A test needing a starting model writes it through the store, not through tools from a
later task. AC3 forces the failure by patching `os.replace`. AC25 speaks raw JSON-RPC lines to a
subprocess so it can check every stdout line.

## Rollout and rollback
Local only. Each task is a branch `task/0001-Tn-short-name` merged to main after the human merge
gate; rollback is reverting that merge. Spec 0001 moves to implemented when T7 merges (build
skill).
