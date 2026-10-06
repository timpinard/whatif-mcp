# Tasks 0001: Model and projection
Rule: each task = one agent session = one reviewable PR.

Spec 0001, Plan 0001. Branch per task: `task/0001-Tn-short-name`. Size guide: under ~400 lines
of non-test code per task.

| ID | Task | Covers AC | Depends on | Status |
|----|------|-----------|------------|--------|
| T1 | Skeleton, dev environment, core types, recurrence, MCP test harness | AC12, AC13 | - | todo |
| T2 | Core projection: growth, flows, caps, period rows, summary, totals | AC14, AC15, AC16, AC17, AC18, AC19, AC20, AC21 | T1 | todo |
| T3 | Store and `show_model` | AC3, AC11 | T1 | todo |
| T4 | Name resolution, `set_account`, `remove_account` | AC4, AC5, AC6, AC7 | T3 | todo |
| T5 | `set_flow`, `remove_flow` | AC8, AC9, AC10 | T4 | todo |
| T6 | `project` tool, today's money, `set_inflation_rate`, read-only file lifecycle, latency | AC1, AC2, AC22, AC23, AC24 | T2, T4 | todo |
| T7 | stdout hygiene and stderr logging | AC25 | T5, T6 | todo |

T2 and T3 can run in parallel. T5 and T6 both register tools in the server; run T5 first to
avoid a conflicting merge. Every AC of Spec 0001 is covered by exactly one task.

## Task notes
- T1: `pyproject.toml` per ADR 0002 with ruff, mypy strict, pytest config and the
  `integration` marker; `python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'` must
  work from a clean checkout. Core: Model, Account, Flow, kind and frequency enums,
  `WhatIfError`; occurrence generation (R9). Server: factory taking a today callable, no
  tools, stdio entry point. `tests/conftest.py`: fixed today, temp model path, in-process
  client session. One smoke integration test so the integration gate has a test to run (Plan
  0001, Risks). Verify and record in the review file: in-process session API, an argument
  named `from`, omitted vs null arguments, and whether the SDK validates input schemas before
  the handler and with what message.
- T2: pure function, horizon end date in, projection out; no rounding inside. Model W core
  builder goes in `conftest.py`.
- T3: path resolved per call; load errors name the path and "not valid JSON" or "version N";
  save writes a temp file in the same dir, chmod 0600, `os.replace`. Model W file builder in
  `conftest.py`.
- T4: name resolution (trim, case-insensitive, exact; error lists existing names) is shared by
  every later tool. Operations are pure functions over a Model (Plan 0001, Approach).
- T5: distinguishes an omitted argument from JSON null; `similar_flows` on every result.
- T6: `project` refuses an empty model naming `set_account`; deflation per R15; neither
  `show_model` nor `project` writes.
- T7: logging configured to stderr at INFO by default (Plan 0001, Spec gaps, item 1); no
  `print`; check that SDK loggers at INFO carry no names or amounts.

## Gate run per task
- T1 to T6: `scripts/gates.sh` with no argument (the AC coverage stage needs every AC of the
  spec and would fail before T7), then show that each covered AC has its test:
  `grep -n "def test_ACn_" tests/test_0001_*.py` for each n the task covers.
- T7: `scripts/gates.sh docs/specs/0001-model-and-projection.md`, which must pass with all 25
  AC covered.

## Per-task Definition of Done
- [ ] Gates pass (scripts/gates.sh output attached, run as in "Gate run per task")
- [ ] Every covered AC has a passing test
- [ ] No spec or ADR drift
- [ ] Regeneration count logged
- [ ] Review file for the task written per conventions.md (gates output + review report)
- [ ] Metrics row added to metrics/log.csv
