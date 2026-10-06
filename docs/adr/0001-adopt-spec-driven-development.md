# ADR 0001: Adopt spec-driven development with agents
- Status: proposed
- Date: 2026-10-06
- Deciders: Timothy Pinard

## Context
whatif-mcp is the pilot project for sdd-kit: building it is also how the kit's artifacts and agents get exercised and filled in.
## Decision
Specs are source of truth. Agents generate plans, code, and reviews. Humans approve spec, plan, and merge.
## Consequences
- Spec quality becomes the bottleneck.
- Fix specs, then regenerate. No hand-patching without updating the spec.
## Alternatives considered
- Prompt-only agent use
- Status quo
