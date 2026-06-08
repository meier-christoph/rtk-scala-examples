#!/usr/bin/env bash
# rtk-scala-examples capture pipeline (PLAN §7). Re-runnable.
#
# For one generated repo (described by its committed .rsx-meta), one build-tool, one
# Scala version, one color mode:
#   stage a real /tmp/workspace copy -> bloopInstall under JDK 21 -> cold clean ->
#   run the situation's command (combined 2>&1) raw, and a parallel rtk-filtered run
#   -> append a savings row.
#
# rtk re-executes commands (no filter-a-file mode), so before/after is two runs;
# valid as A/B only because capture is strongly deterministic (PLAN #18/#19/#20/#21).
#
# Phase 1 scope: bloop, Scala 3, nocolor. Other axes are wired but exercised later.
#
# Usage: scripts/capture.sh <repo-name> [--tool bloop|sbt|sbtn] [--scala 3|213] [--color nocolor|color]

set -euo pipefail

RSX_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RSX_ROOT="$(cd "$RSX_HERE/.." && pwd)"
export RSX_ROOT
# shellcheck source=lib.sh
source "$RSX_HERE/lib.sh"

RTK_DIR="${RTK_DIR:-$(cd "$RSX_ROOT/../rtk" && pwd)}"
RTK_BIN="${RTK_BIN:-$RTK_DIR/target/release/rtk}"

# ---- args -------------------------------------------------------------------
NAME=""; TOOL="bloop"; SCALA="3"; COLOR="nocolor"; REFILTER=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --tool) TOOL="$2"; shift 2 ;;
    --scala) SCALA="$2"; shift 2 ;;
    --color) COLOR="$2"; shift 2 ;;
    --refilter) REFILTER=1; shift ;;   # reuse the existing raw .txt; only re-run rtk
    -*) rsx_die "unknown flag: $1" ;;
    *) NAME="$1"; shift ;;
  esac
done
[ -n "$NAME" ] || rsx_die "usage: capture.sh <repo-name> [--tool bloop] [--scala 3] [--color nocolor|color]"
[ "$TOOL" = "bloop" ] || rsx_die "tool '$TOOL' not yet wired (Phase 1 = bloop only)"
[ "$SCALA" = "3" ] || rsx_die "scala '$SCALA' not yet wired (Phase 1 = Scala 3 only)"

# ---- read the repo's metadata (no name parsing) -----------------------------
META="$RSX_ROOT/repos/$NAME/.rsx-meta"
[ -f "$META" ] || rsx_die "no .rsx-meta in repos/$NAME (run generator/gen.py first)"
# shellcheck disable=SC1090
source "$META"   # LIB STYLE SITUATION SCALE TOPOLOGY AGNOSTIC COMMAND PROJECTS

# ---- fixture name (PLAN §6) -------------------------------------------------
VER_TOK="3"
VARIANT=""; [ "$COLOR" = "color" ] && VARIANT="_color"
if [ "$TOPOLOGY" = "mm" ]; then
  base="${TOOL}_${COMMAND}_mm_${LIB}_${STYLE}_${SITUATION}_${SCALE}"
elif [ "$AGNOSTIC" = "1" ]; then
  base="${TOOL}_${COMMAND}_${SITUATION}${SCALE:+_$SCALE}"
else
  base="${TOOL}_${COMMAND}_${LIB}_${STYLE}_${SITUATION}_${SCALE}"
fi
FIXNAME="${base}${VARIANT}_${VER_TOK}"

OUTDIR="$RSX_ROOT/fixtures/$TOOL"
mkdir -p "$OUTDIR"
RAW="$OUTDIR/$FIXNAME.txt"
FILTERED="$OUTDIR/$FIXNAME.rtk.txt"
CSV="$OUTDIR/savings.csv"
rsx_init_savings "$CSV"

rsx_rtk_supports() {
  [ -x "$RTK_BIN" ] || return 1
  "$RTK_BIN" --help 2>&1 | grep -qiw "$1"
}

# ---- pipeline ---------------------------------------------------------------
rsx_pin_env "$COLOR"
WS="$(rsx_stage_workspace "$NAME")"
rsx_info "staged $WS  [$FIXNAME]"

rsx_bloop_install "$WS"
rsx_bloop_restart
rsx_info "bloopInstall done, server bounced (JDK 21); projects: $PROJECTS"

read -r -a PROJ <<<"$PROJECTS"

# Put the build into the situation's starting state. CRITICAL for before/after
# validity (PLAN #19): rtk *re-executes* the command, so the raw run must NOT warm
# the cache for the rtk run — otherwise a cold compile becomes a misleading
# "up-to-date" on the second pass and all warnings/compile lines vanish. So we
# reset to the same state before BOTH the raw and the rtk run.
#   - incremental: warm once so both runs are deterministic no-ops (PLAN #18)
#   - everything else: clean so both runs compile cold
rsx_prepare_state() {
  if [ "$SITUATION" = "incremental" ]; then
    ( cd "$WS" && bloop "$COMMAND" "${PROJ[@]}" ) >/dev/null 2>&1 || true
  else
    ( cd "$WS" && bloop clean "${PROJ[@]}" ) >/dev/null 2>&1 || true
  fi
}

if [ "$REFILTER" = "1" ]; then
  # Refresh only the rtk-filtered side against the current rtk binary; the raw .txt is
  # rtk-independent (PLAN #19) so we keep it byte-for-byte and re-use it for savings.
  [ -f "$RAW" ] || rsx_die "refilter: raw fixture missing ($RAW) — run a full capture first"
  rsx_info "refilter: keeping existing raw $RAW"
else
  rsx_prepare_state
  rsx_info "capturing raw: bloop $COMMAND ${PROJ[*]} -> $RAW"
  ( cd "$WS" && bloop "$COMMAND" "${PROJ[@]}" ) >"$RAW" 2>&1 || true
fi

if rsx_rtk_supports "$TOOL"; then
  rsx_prepare_state   # reset so rtk's re-execution sees the same cold/warm state
  rsx_info "capturing rtk-filtered: rtk $TOOL $COMMAND ${PROJ[*]}"
  # stdout only: rtk's filtered result is on stdout; the rate-limited "[rtk] /!\\ No
  # hook installed" advisory is a stderr side-channel that would make this artifact
  # non-deterministic. (Eval-only file; the shippable raw .txt keeps full 2>&1.)
  ( cd "$WS" && "$RTK_BIN" "$TOOL" "$COMMAND" "${PROJ[@]}" 2>/dev/null ) >"$FILTERED" || true
  rsx_savings_row "$CSV" "$FIXNAME" "$RAW" "$FILTERED"
else
  rsx_info "rtk does not handle '$TOOL' yet — skipping filtered capture (PLAN #15)"
  rm -f "$FILTERED"
  rsx_savings_row "$CSV" "$FIXNAME" "$RAW" ""
fi

rsx_info "done: $FIXNAME ($(rsx_token_count "$RAW") raw tokens)"
