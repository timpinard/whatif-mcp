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
