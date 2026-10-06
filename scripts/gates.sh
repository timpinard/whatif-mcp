#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== lint ==";        .venv/bin/ruff format --check . && .venv/bin/ruff check .
echo "== typecheck ==";   .venv/bin/mypy src
echo "== unit ==";        .venv/bin/pytest -q -m "not integration"
echo "== integration =="; .venv/bin/pytest -q -m integration
echo "== AC coverage =="
# Fails if any AC id in the spec has no matching test in that spec's test files
SPEC="${1:-}"
if [ -n "$SPEC" ]; then
  SPEC_ID="$(basename "$SPEC" | grep -oE '^[0-9]{4}')"
  SPEC_TESTS=(tests/test_"${SPEC_ID}"_*.py)
  [ -e "${SPEC_TESTS[0]}" ] || { echo "No tests/test_${SPEC_ID}_*.py for $SPEC"; exit 1; }
  for ac in $(grep -oE 'AC[0-9]+' "$SPEC" | sort -u); do
    grep -q "def test_${ac}_" "${SPEC_TESTS[@]}" || { echo "Missing test for $ac"; exit 1; }
  done
fi
echo "ALL GATES PASSED"
