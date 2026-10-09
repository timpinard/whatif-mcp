# Tasks 0002: What-if
- Plan: Plan 0002
Each task is a **vertical slice**: a task that cuts thinly through every layer it needs to deliver
one behavior a user can see, as opposed to a layer-only task. Demoable or verifiable on its own, one
agent session, one reviewable branch.

`$S` below is `docs/specs/0002-what-if.md`.

| ID | Vertical slice (what works afterwards, in user terms) | Covers AC | Blocked by | Gate command | Jira | Status |
|----|--------------------------------------------------------|-----------|------------|--------------|------|--------|
| T1 | The user asks "what if" with one or more changes and gets the comparison, nominal or in today's money; the file is never written | AC1, AC2, AC3, AC4, AC5, AC6, AC8, AC10 | - | `scripts/gates.sh $S AC1 AC2 AC3 AC4 AC5 AC6 AC8 AC10` | | done |
| T2 | Bad change lists are refused clearly, each by its position | AC7, AC9 | T1 | `scripts/gates.sh $S AC7 AC9` | | done |
| T3 | Renamed and re-added accounts and flows line up with their baseline | AC11 | T2 | `scripts/gates.sh $S` | | done |
| T4 | `applied` names sub-cent changes; a re-created name resumes its own baseline entry; change lists are capped at 1,000; account blocks state their kind | AC12, AC13, AC14, AC15 | T3 | `scripts/gates.sh $S` | | done |

Every AC of Spec 0002 is in exactly one task. T4 was added after the QA pass (QA 0002 record). T2 and T3 run in sequence: both edit
`server/operations/what_if.py` (Plan 0002, Approach).

## Task notes (per task: test boundaries, interfaces it creates or changes, decisions already taken)
- T1 (S3): creates `core/comparison.py`, `server/operations/what_if.py`, `server/tools/what_if.py`
  and registers `what_if` in `app.py`. Entries are matched by name (T3 adds rename tracking).
  Applying the change list is a function separate from the comparison (Spec 0003 reuses it).
  Every money value, differences included, goes through the reportable check (Spec 0002 R2,
  amended): add a `test_R2_` test. `applied` follows amended R3 for updates, creates and removes.
  Projection arguments via `parse_project_arguments`; defaults and errors as `project`. AC8
  compares bytes and `st_mtime_ns`. Over ~400 non-test lines: stop and move AC10 to a T1b that
  blocks T2 (Plan 0002, Risks).
- T2 (S3): change-list validation (empty list, non-object change, missing or non-text `op`,
  unknown op, hypothetical with no accounts; baseline with no accounts checked before any change)
  and the "change N: " prefix on every error raised while applying change N. Unknown keys inside a
  change reuse the registry's argument-name check against the op's tool definition. Adds
  `test_R6_` tests for each malformed shape and a seeded robustness test of hostile change lists
  asserting no internal error, in the style of `test_R16_no_tool_returns_an_internal_error`.
- T3 (S3): R7 matching tracked while applying changes: a map from hypothetical name to baseline
  name (or none). Rename keeps the entry; remove ends it; create resumes an entry removed earlier
  under that name. Entry order: baseline order, then hypothetical-only entries in creation order.
  Adds a `test_R7_` test for a rename onto a name removed earlier (two entries share the name).
  Last task: runs the full gate, sets Spec 0002 Status: implemented, adds the metrics row, then the
  owner gate to merge `spec/0002-what-if` to main.
- T4 (S3): QA fixes (QA 0002 record, F1, F2, F3, F5, F6). `applied` compares unrounded fields as
  the tools do (F1). R7 resume order: a removed entry whose baseline name matches first, else the
  most recently removed under that name (F2, F6). More than 1,000 changes refused with the
  change-list shape checks, naming changes (F3). `kind` in each side's account block (F5). Last
  task again: full gate, Spec 0002 Status implemented (build skill), metrics row.

## Per-task Definition of Done
- [ ] Gate command green, output in the review record
- [ ] Every covered AC has a passing test at its test boundary, seen red (written red first, or
  broken on purpose and recorded)
- [ ] Spec-review and standards-review findings resolved or waived by the owner
- [ ] No spec or ADR drift
