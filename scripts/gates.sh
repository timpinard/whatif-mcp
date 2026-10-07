#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== references =="
DOCS=(AGENTS.md $(find docs -name '*.md' -not -path 'docs/reviews/*' -not -path 'docs/retro/*' -not -name 'kit-feedback.md'))
for ref in $(grep -ohE '(ADR|Epic|Spec|Plan) [0-9]{4}' "${DOCS[@]}" | tr ' ' '_' | sort -u); do
  kind="${ref%_*}"; id="${ref#*_}"
  case "$kind" in ADR) dir=docs/adr ;; Epic) dir=docs/epics ;; Spec) dir=docs/specs ;; Plan) dir=docs/plans ;; esac
  ls "$dir/$id"-*.md >/dev/null 2>&1 || { echo "Dangling reference: ${kind} ${id}"; exit 1; }
done
for path in $(grep -ohE 'docs/[A-Za-z0-9_./-]+\.md' "${DOCS[@]}" | grep -v NNNN | sort -u); do
  [ -e "$path" ] || { echo "Dangling path: $path"; exit 1; }
done
# One command per line: under set -e, a failure on the left of && or || does not stop the script.
tests_at_level() {
  local status=0
  "$@" || status=$?
  [ "$status" -eq 5 ] && { echo "(no tests at this level yet)"; return 0; }
  return "$status"
}
echo "== lint =="
uv run --locked ruff format --check .
uv run --locked ruff check .
echo "== typecheck =="
uv run --locked mypy src
echo "== unit =="
tests_at_level uv run --locked pytest -q -m "not integration"
echo "== integration =="
tests_at_level uv run --locked pytest -q -m integration
echo "== AC coverage =="
# With a spec: every AC listed after it (or every AC in the spec when none are listed) needs a
# `def test_ACn_` in that spec's tests/test_NNNN_*.py files.
SPEC="${1:-}"
if [ -n "$SPEC" ]; then
  shift
  SPEC_ID="$(basename "$SPEC" | grep -oE '^[0-9]{4}')"
  SPEC_TESTS=(tests/test_"${SPEC_ID}"_*.py)
  [ -e "${SPEC_TESTS[0]}" ] || { echo "No tests/test_${SPEC_ID}_*.py for $SPEC"; exit 1; }
  if [ "$#" -gt 0 ]; then ACS="$*"; else ACS="$(grep -oE 'AC[0-9]+' "$SPEC" | sort -u)"; fi
  for ac in $ACS; do
    grep -q "def test_${ac}_" "${SPEC_TESTS[@]}" || { echo "Missing test for $ac"; exit 1; }
  done
fi
echo "ALL GATES PASSED"
