#!/usr/bin/env bash
# Stamp the full repo set. Phase 1 = munit (representative) situation set + agnostic
# situations (small+large) + the first multimodule repo. Deterministic; re-runnable.
#
# Usage: scripts/gen-all.sh [phase1]   (phase1 is the default and only set for now)

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEN="$(cd "$HERE/.." && pwd)/generator/gen.py"

g() { python3 "$GEN" "$@"; }

# --- munit representative: per-situation, small + large -----------------------
for scale in small large; do
  g --lib munit --style funsuite --situation pass      --scale "$scale"
  g --lib munit --style funsuite --situation fail      --scale "$scale"
  g --lib munit --style funsuite --situation error     --scale "$scale"
  g --lib munit --style funsuite --situation warn_fail --scale "$scale"
done
# skipped is small-only (PLAN situation table)
g --lib munit --style funsuite --situation skipped --scale small

# --- agnostic situations ------------------------------------------------------
for scale in small large; do
  g --situation warn          --scale "$scale"
  g --situation compile_error --scale "$scale"
done
g --situation compile_pass    # scale-less
g --situation incremental     # scale-less
g --situation no_tests        # scale-less

# --- first multimodule repo ---------------------------------------------------
g --lib munit --situation fail --scale small --topology mm

echo "gen-all: done"
