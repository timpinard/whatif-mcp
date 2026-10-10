# Follow-ups
Findings waived as a separate task, and QA findings deferred. The retro reviews this list.

| Date | Source | Item | Decision |
|------|--------|------|----------|
| 2026-10-09 | QA 0002 F7 | Errors echo the whole offending value (a 5 MB string returns a 5,000,070-character error; nested values in full). The echo is in argument parsing shared by every tool; a Spec 0001 follow-up. | |
| 2026-10-09 | Review 0002-T4 Z1 | Three copies of "fields that differ": what_if `_changed_keys`, `shaping.shape_flow_changes` and `tools/accounts._shape_account_edit`. | |
| 2026-10-09 | Review 0002-T3 X1, W1 | store.py keeps its own `name.strip().casefold()`, so the name-matching rule lives in two places; check whether store importing from server/operations crosses a layer first. | |
