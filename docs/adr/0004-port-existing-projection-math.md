# ADR 0004: Port the the source project projection math rather than share it
- Status: proposed
- Date: 2026-10-06
- Deciders: Timothy Pinard

## Context
the source project's `engine/evaluator.py` already does recurrence dates, period bucketing, flow
evaluation, double-entry application and Monte Carlo bands, and its what-if and solve-for tools
are tested. But it reads inputs from and writes results to Postgres, and its what-if works by
writing a temporary plan and rolling the transaction back.

## Decision
Port the behavior into `whatif_mcp.core` as pure functions over in-memory data. Do not import or
vendor the source project code, and do not change the source project. Use the source project's tests and engine
outputs as the reference for expected numbers (parity fixtures).

## Consequences
- What-if becomes copy, change, project twice, compare; no rollback trick.
- Two copies of the math can drift. Accepted: the source project may later depend on this core, as a
  separate decision.
- Behaviors not ported are listed as non-goals in the spec (tax withholding among them).

## Alternatives considered
- Extract a shared library used by both: right long-term, but it changes the source project first and
  couples the pilot to it.
- Fresh rewrite without reference: loses tested behavior and the parity check.
