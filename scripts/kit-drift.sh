#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
KIT="${SDD_KIT_PATH:-$HOME/Workspace/sdd-kit}"
[ -f .sdd-kit ] || { echo "No .sdd-kit stamp: this project does not record its kit version"; exit 1; }
[ -d "$KIT/.git" ] || { echo "Kit not found at $KIT (set SDD_KIT_PATH)"; exit 1; }
STAMP="$(tr -d '[:space:]' < .sdd-kit)"
LATEST="$(git -C "$KIT" describe --tags --abbrev=0)"
if [ "$STAMP" = "$LATEST" ]; then
  echo "Kit up to date: $STAMP"
  exit 0
fi
echo "Kit drift: project on $STAMP, kit at $LATEST. Changes since $STAMP:"
echo
awk -v stamp="$STAMP" '/^## v/ && $2 == stamp {exit} /^## v/ {show=1} show' "$KIT/CHANGELOG.md"
echo "Kit-owned files changed (kit-manifest):"
PATHS=$(awk '!/^#/ && ($1 == "kit" || $1 == "mixed") {print $2}' "$KIT/kit-manifest")
git -C "$KIT" diff --stat "$STAMP" "$LATEST" -- $PATHS
echo
echo "Adopt or skip each entry, then set .sdd-kit to $LATEST and commit listing what was taken."
