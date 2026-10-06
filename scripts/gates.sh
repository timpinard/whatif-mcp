#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== references =="
DOCS=(AGENTS.md $(find docs -name '*.md'))
for ref in $(grep -ohE '(ADR|Spec) [0-9]{4}' "${DOCS[@]}" | tr ' ' '_' | sort -u); do
  kind="${ref%_*}"; id="${ref#*_}"
  dir=docs/adr; [ "$kind" = Spec ] && dir=docs/specs
  ls "$dir/$id"-*.md >/dev/null 2>&1 || { echo "Dangling reference: ${kind} ${id}"; exit 1; }
done
for path in $(grep -ohE 'docs/[A-Za-z0-9_./-]+\.md' "${DOCS[@]}" | grep -v NNNN | sort -u); do
  [ -e "$path" ] || { echo "Dangling path: $path"; exit 1; }
done
echo "== lint =="
uv run --locked ruff format --check .
uv run --locked ruff check .
echo "== typecheck ==";   uv run --locked mypy src
echo "== unit ==";        uv run --locked pytest -q -m "not integration"
echo "== integration =="; uv run --locked pytest -q -m integration
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
