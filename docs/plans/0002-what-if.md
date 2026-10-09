# Plan 0002: What-if
- Spec: Spec 0002
- Status: approved
- Approved by: Timothy Pinard, 2026-10-08; T4 added after the QA pass, approved by Timothy Pinard,
  2026-10-09
- Jira:

## Approach
Three vertical slices, run in sequence on the integration branch `spec/0002-what-if` (Tasks 0002):
T1 delivers the whole comparison for the common case, T2 the refusals, T3 rename matching. T2 and
T3 both edit `server/operations/what_if.py`, so they run one after the other, not in parallel.

Decisions taken in the quiz (2026-10-08, Timothy Pinard):
- The editing operations from Plan 0001 (`server/operations/accounts.py`, `flows.py`) are reused
  unchanged on an in-memory copy. `server/operations/what_if.py` parses the change list, applies
  each change through them in order, tracks R7 matching and writes the `applied` descriptions.
  Applying changes is separate from comparing, so Spec 0003 can apply one `set_flow` change and
  measure without a comparison.
- `core/comparison.py` takes the baseline and hypothetical projections plus the entry matching and
  returns unrounded differences. Rounding happens only in shaping.
- `server/tools/what_if.py` is the handler: load the model once, check the baseline has accounts,
  apply the changes, check the hypothetical has accounts, project both, deflate both when
  `in_todays_money`, check every money value (both projections and the differences), compare,
  shape. Registered in `app.py`. It never writes.
- No internal account id and no file format change (left to this plan by Plan 0001). R7 matching
  is tracked by name while changes are applied: a map from each hypothetical name to its baseline
  name, or none for a new entry.
- An unknown key inside a change is refused as the tool would refuse it (R1, "exactly as that tool
  would"), by reusing the registry's argument-name check against the op's tool definition, with
  the change's position.
- `core/todays_money.py` stays as it is (left to this plan by Plan 0001): `what_if` runs the
  reportable check on both deflated projections, as `project` does.
- Entry order in `accounts` and `flows`: baseline order (a renamed entry keeps its baseline
  position), then entries that exist only in the hypothetical, in creation order.
- Projection arguments (`horizon_years`, `granularity`, `in_todays_money`) are parsed by the
  existing `parse_project_arguments`.

QA fix task (2026-10-09). The QA pass on the implemented spec found one bug and seven gaps
(QA 0002 record); the owner amended Spec 0002 (R3, R6, R7; AC12 to AC15). One slice, T4: unrounded
`applied` comparison (F1), R7's resume order (F2, F6), the 1,000-change limit (F3), `kind` in the
account blocks (F5). The limit is checked with the change-list shape, before the file is loaded.
AC12 to AC15 at S3; no new test boundary.

## Test boundaries (agreed with the owner)
A test boundary is the public boundary a test drives the system through and observes results at,
e.g. a core function, the store, the tool layer over an in-process client.

Agreed 2026-10-08 by Timothy Pinard (engineer); QA review of what each boundary misses: Timothy
Pinard.

| Test boundary | What it catches | What it misses |
|---------------|-----------------|----------------|
| S3 MCP tools through the in-process client (integration), as in Plan 0001. AC1 to AC11 | Change application and order, every error message and position, the comparison numbers to the cent, one-sided entries, entry matching, rounding and shape, file bytes and mtime unchanged | stdio framing and logging (unchanged code path, covered by Spec 0001 AC25); the real clock; that the file is read once per call |

Not observed by S3, checked by review: the model file is read once per call (Spec 0002,
Constraints). Behavior with no AC gets its own tests: `test_R2_` (the money limit on a difference),
`test_R6_` (every malformed change shape), `test_R7_` (a rename onto a name removed earlier), and a
seeded robustness test that sends hostile change lists to `what_if` and asserts no internal error.
AC8 compares `st_mtime_ns` as well as bytes, so a rewrite of identical bytes is caught.

## Components touched
- `whatif_mcp.core`: new `comparison.py` (T1). Projection, deflation and recurrence unchanged.
- `whatif_mcp.server`: new `operations/what_if.py` (T1, extended by T2 and T3), new
  `tools/what_if.py` (T1), `app.py` registers it (T1). The registry's argument-name check is
  reused, not changed in behavior (T2).
- `whatif_mcp.store`: unchanged; `what_if` uses `load_model` only.
- `tests/`: per Test layout.

## Data / schema changes
None. The model file format stays version 1.

## ADR conformance (list ADRs checked)
- ADR 0001: every AC of Spec 0002 lands in exactly one task; nothing beyond the spec. Conforms.
- ADR 0002: no new runtime or dev dependency. Conforms.
- ADR 0003: the file is read and never written by `what_if`. Conforms.
- ADR 0004: copy, change, project twice, compare, in memory; no rollback trick. Conforms.
- ADR 0005: gates through `uv run --locked`. Conforms.
- No conflicts found.

## Risks and unknowns
- T1 is the largest slice (~330 non-test lines estimated). If it passes ~400, AC10 (today's money
  and projection options) moves to a T1b that blocks T2.
- A projection runs twice per call; R18's budget (under 1 s for 30 years) is set for `project`.
  `what_if` has no latency requirement; two projections stay well inside 1 s on Model W sizes.
- Floating point: differences are taken from unrounded values (AC4's 277.71, not 277.72). The
  "differs to the cent" flow filter compares rounded totals.
- Re-adding a removed flow places it last in the hypothetical's flow order, which can change
  same-day order (Spec 0001 R12). Correct by the spec; AC11's re-add case has no same-day effect.

## Spec gaps (flagged for the owner; working assumption in brackets; resolved by amending the spec)
Resolved by the owner on 2026-10-08 at the quiz and amended into Spec 0002:
1. The money limit and differences. [Every money value in the result, differences included, is
   held to Spec 0001 R14's limit with the same error as `project`.] R2.
2. `applied` wording for creates and removes. [A create names the op, the name, that it was
   created and each given field's value; a remove names the op and the name.] R3.

## Test layout (test files, which task owns each, shared fixtures)
| File | AC | Test boundary | Task |
|------|----|---------------|------|
| tests/test_0002_comparison.py | AC1, AC2, AC3, AC4, AC5, AC6, AC10 (+ test_R2_) | S3 | T1 |
| tests/test_0002_read_only.py | AC8 | S3 | T1 |
| tests/test_0002_refusals.py | AC7, AC9 (+ test_R6_, robustness) | S3 | T2 |
| tests/test_0002_matching.py | AC11 (+ test_R7_) | S3 | T3 |
| tests/test_0002_qa_fixes.py | AC12, AC13, AC14, AC15 | S3 | T4 |

Shared fixtures: `client`, `model_w`, `model_w_file`, `write_model_file` from `tests/conftest.py`,
unchanged. A helper that calls `what_if` and returns the structured result goes in
`tests/helpers.py` (T1).

## Rollout and rollback
Local only. Each task is a branch `task/0002-Tn-short-name` cut from `spec/0002-what-if` and merged
into it at the human merge gate. After T3 merges and the full `scripts/gates.sh <spec>` passes,
the owner merges `spec/0002-what-if` to main. Rollback is reverting that merge.
