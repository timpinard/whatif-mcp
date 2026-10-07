# Kit feedback
Problems with the process found while working in this project. Do not change the kit from here;
the retro decides (see the kit README, Process lifecycle).

| Date | Stage | Artifact | Problem | Suggestion | Retro decision |
|------|-------|----------|---------|------------|----------------|
| 2026-10-06 | Spec | ticket-agent.md | Rule "AC ids only in the AC table and Covers" contradicts the template's Open questions column "AC that depend on it" | Reword: mention only AC ids that exist in this spec's AC table | |
| 2026-10-06 | Spec | AGENTS.md rule 7 | Unclear whether the product's own paths (e.g. its default model file path) count as naming a file | Say "external": other systems and repos, not the product's own interface | |
| 2026-10-06 | Spec | ticket-agent.md | Bash is allowed for "reading and arithmetic only"; the agent used it once to edit a spec. The tool list cannot enforce the restriction | Either accept it or drop Bash and give arithmetic another route | |
| 2026-10-06 | Spec | _template-spec.md | An AC stated a difference of rounded figures (277.72) while the rounding rule needs the unrounded one (277.71); caught by hand-checking | Add a "Numbers: precision and rounding" prompt under Interfaces and data shapes | |
| 2026-10-06 | Setup | scripts/gates.sh | `a && b` on one gate line does not stop the script under set -e when a fails; the lint gate carried on | One command per line; say so beside the placeholders | |
| 2026-10-06 | Spec | conventions.md (project) | No rule for how the log level is set, so a logging AC had to assume INFO | Project only: add to conventions.md | |
| 2026-10-06 | Intent | (missing) | No PO artifact: the flow starts at the spec, so the epic description and success measures had to be reconstructed afterwards | Promote docs/epics/_template-epic.md to the kit; add an Epic stage before Intent with the PO as owner | |
| 2026-10-06 | All | (missing) | No mapping from SDD artifacts and gates to tracker issues and transitions | Promote docs/jira.md to the kit as a tracker-neutral mapping | |
| 2026-10-06 | All | AGENTS.md rule 7 | Tracker keys are external IDs, but every doc needs one | Allow a `Jira:` (tracker key) header line in epics, specs, plans and tasks | |
| 2026-10-06 | Spec | _template-spec.md | No approval line, so an approved spec does not say who approved it or when | Add `- Approved by:` as in the plan template | |
| 2026-10-06 | Plan | scripts/gates.sh | pytest exits 5 when a level has no tests, so gates cannot pass until one unit and one integration test exist | Treat exit 5 as pass for a level, or require a smoke test per level in the first task | |
| 2026-10-06 | Plan | scripts/gates.sh, implementer.md | AC coverage is all-or-nothing per spec, so it fails on every task but the last; implementer.md says always pass the spec | Accept AC ids after the spec (`gates.sh SPEC AC1 AC4`) and check only those; full check on the last task | |
| 2026-10-06 | Plan | references gate | Cannot name files that later tasks will create (docs/reviews/NNNN-Tn.md) | Skip paths under docs/reviews/, or refer to reviews by task ID | |
| 2026-10-06 | Plan | _template-plan.md, _template-tasks.md | No place for spec gaps, test-file split and fixture ownership, or per-task notes and interface contracts | Add Spec gaps, Test layout and Task notes sections | |
| 2026-10-06 | Plan | planner.md | Silent on: greenfield setup task, per-task gate command, task size limit, whether to choose implementation details (SDK style, module seams), whether to plan for later specs | State each explicitly | |
| 2026-10-06 | Plan | _template-plan.md vs AGENTS.md rule 7 | Template header `Spec: docs/specs/...` is a path; rule 7 says refer by ID | Template: `Spec: Spec NNNN` | |
| 2026-10-06 | Done | definition-of-done.md | Nobody is assigned to set spec Status: implemented or add the metrics row | Assign to the implementer of the spec's last task | |
| 2026-10-06 | Plan | _template-adr.md | Superseding only part of an accepted ADR (ADR 0002's environment line, by ADR 0005) has no defined status form | Allow `accepted; <part> superseded by NNNN` in the template | |
| 2026-10-06 | Plan | (process) | Amending an approved spec before implementation has no defined form | Add an `Amended:` header line and a rule: amendments name the R ids changed and are owner-approved | |
| 2026-10-06 | Build | metrics/log.csv, Tasks DoD | The implementer adds the metrics row, but review_findings_agent, review_findings_human and cycle_time_hours are unknown until review and merge | Say who fills those columns and when (reviewer and merge gate), or move the row to the merge step | |
