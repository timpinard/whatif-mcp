# Tasks 0001: Model and projection
- Plan: Plan 0001
Each task is a **slice**: a thin path through every layer it needs, demoable or verifiable on its
own, one agent session, one reviewable branch.

`$S` below is `docs/specs/0001-model-and-projection.md`.

| ID | Slice (what works afterwards, in user terms) | Covers AC | Blocked by | Gate command | Jira | Status |
|----|-----------------------------------------------|-----------|------------|--------------|------|--------|
| T1 | Skeleton, dev environment, core types, recurrence, MCP test harness | AC12, AC13 | - | `scripts/gates.sh` + grep (sdd-kit 0.1) | | done |
| T2 | The core projects any model forward: rows per period, account summary, flow totals (unrounded) | AC14, AC15, AC16, AC17, AC18, AC19, AC20, AC21 | - | `scripts/gates.sh $S AC14 AC15 AC16 AC17 AC18 AC19 AC20 AC21` | | done |
| T3 | `show_model` shows the model file, money rounded half up; writes are atomic | AC3, AC11, AC26 | - | `scripts/gates.sh $S AC3 AC11 AC26` | | done |
| T4 | The user builds and corrects accounts | AC4, AC5, AC6, AC7 | T3 | `scripts/gates.sh $S AC4 AC5 AC6 AC7` | | todo |
| T5 | The user asks "where will I be", nominal or in today's money | AC1, AC2, AC22, AC23, AC24 | T2, T4 | `scripts/gates.sh $S AC1 AC2 AC22 AC23 AC24` | | todo |
| T6 | The user builds and corrects flows | AC8, AC9, AC10 | T4 | `scripts/gates.sh $S AC8 AC9 AC10` | | todo |
| T7 | The server runs cleanly under a real client: stdout is MCP only, logs on stderr | AC25 | T5, T6 | `scripts/gates.sh $S` | | todo |

T2 and T3 run in parallel; so do T5 and T6. Every AC of Spec 0001 is in exactly one task.

## Task notes (per task: seams, interfaces it creates or changes, decisions already taken)
- T2 (S1, layer-only by Plan 0001, Approach): one pure function, (model, today, horizon end,
  granularity) in, projection out, no rounding inside. Event-driven by date. Exposes balances
  after the events of any date in range (Spec 0003) and computes one account's growth on one
  date in a single function (Spec 0004). Occurrences filtered to strictly after today and on or
  before the horizon end; `occurrence_dates` is unchanged. Model W core builder in
  `conftest.py`. Over ~400 non-test lines: stop and split AC15 and AC21 into T2b (Plan 0001,
  Risks).
- T3 (S2, S3): store module: path resolved per call; load errors name the path and "not valid
  JSON", "version N" or the shape problem; save writes a temp file in the same directory, chmod
  0600, `os.replace`, creating parent directories. Server: tool registry with one module per tool
  group, `app.py` only concatenates (Plan 0001, Approach); `WhatIfError` -> tool error with
  `isError: true`; the half-up cents helper; `show_model`. Store-backed model file builder and
  Model W file form in `conftest.py`.
- T4 (S3): name resolution (trim, case-insensitive, exact; error lists existing names), shared
  by T5 and T6. Account operations are pure functions over a Model. `kind` may change on update;
  the resulting account is validated as new (Spec 0001 R2, amended). Numbers: a JSON boolean is
  not a number.
  Each account rule lives once, in core, as a check on `Account`; `set_account` and the store
  loader both call it, so a file account breaking an R2 rule is a shape error (Spec 0001 R1,
  amended at the Task 0001-T3 merge gate).
- T5 (S3): `project` arguments and shaping (R13, R14), deflation in core (R15),
  `set_inflation_rate` (R6), empty model names `set_account`; neither `show_model` nor `project`
  writes. AC1 and AC2 use `set_account` from T4.
- T6 (S3): omitted vs JSON null; fixed/rate switching; `similar_flows` on every result; on
  update the resulting flow is validated as new, the never-fires check only when start_date or
  frequency is given; `rate_of` without `rate` per Spec 0001 R4 (amended).
  Each flow rule (amount or rate with rate_of, ranges) lives once, in core, as a check on `Flow`;
  `set_flow` and the store loader both call it, replacing the loader's partial check and the
  `assert` in `core/projection.py` (Spec 0001 R1, amended at the Task 0001-T3 merge gate).
- T7 (S4): logging to stderr at INFO, no knob; no `print`; check SDK loggers at INFO carry no
  names or amounts. The AC25 test also makes one rejected call (Plan 0001, Seams).

## Per-task Definition of Done
- [ ] Gate command green, output in the review record
- [ ] Every covered AC has a passing test at its seam, written red first
- [ ] Spec-review and standards-review findings resolved or waived by the owner
- [ ] No spec or ADR drift
