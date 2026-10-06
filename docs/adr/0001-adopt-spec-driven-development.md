# ADR 0001: Adopt spec-driven development with agents
- Status: proposed
- Date:

## Context
<why: throughput, consistency, review load>
## Decision
Specs are source of truth. Agents generate plans, code, and reviews. Humans approve spec, plan, and merge.
## Consequences
- Spec quality becomes the bottleneck.
- Fix specs, then regenerate. No hand-patching without updating the spec.
## Alternatives considered
- Prompt-only agent use
- Status quo
