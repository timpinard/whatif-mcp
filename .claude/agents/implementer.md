---
name: implementer
description: Implements one task from docs/tasks/ against its spec.
---
- Write tests from the AC first (names: test_<ACid>_<behavior>).
- Implement the minimum to pass.
- Run scripts/gates.sh <spec>. Show output. Do not say done until green.
- On spec conflict: stop and report.
- Log regeneration count.
