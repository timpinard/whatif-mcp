# ADR 0004: Port an existing projection engine's math rather than share it
- Status: accepted
- Date: 2026-10-06
- Deciders: Timothy Pinard

## Context
The source engine is the source project's `engine/evaluator.py` and `engine/function_registry.py`, as of
the source project commit c03c1e2. It does recurrence dates, period bucketing, flow evaluation,
double-entry application, Monte Carlo bands, what-if and solve-for. It reads inputs from and writes
results to Postgres, and its what-if works by writing a temporary plan and rolling it back. It also
has defects found while specifying this project (month-end drift, semimonthly skips, payments past
payoff, unconverged solve-for reported as success).

## Decision
Port the behavior into `whatif_mcp.core` as pure functions over in-memory data. Do not import or
vendor the source code, and do not change the source project. Fix its known defects in the port
rather than reproduce them. Expected numbers in tests are hand-checked, not recorded from the
source engine.

## Consequences
- What-if becomes copy, change, project twice, compare; no rollback trick.
- Two copies of similar math can drift. Accepted: the source project may later depend on this
  core, as a separate decision.
- Specs and living docs call it "the source engine (ADR 0004)"; only this record names it.

## Alternatives considered
- Extract a shared library used by both: right long-term, but changes the source project first.
- Parity fixtures recorded from the source engine: needs its database running, and the fixed
  defects leave few inputs where the two should agree.
- Fresh rewrite without reference: loses tested behavior.
