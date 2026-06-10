#!/usr/bin/env bash
# Real-repo fixture capture for the rtk bloop filter — LOCAL-ONLY track.
#
# Separate from the generated rig (generator/, repos/, scripts/). Captures real
# build/test output from well-known Scala repos (cloned at a pinned tag, with a
# minimal build tweak + a committed failure patch) and runs it through rtk for a
# before/after A/B. Outputs land in fixtures/real/bloop/ (NOT fixtures/bloop/).
#
# Usage:   real/capture-real.sh <repo> <situation>
#   repo:       circe | enumeratum | zio-json | cats-effect
#   situation:  test_pass | test_fail | test_error | compile_pass | compile_error | compile_warn | all
#               (Play: compile_* run the multimodule-large cascade on Play-Netty-Server;
#                test_* run on the Play core module — ~40s cold, 81 specs2 suites)
#
# Encodes the verified rig facts (PLAN §7, §3 #18-#21):
#   - pin JDK 21 via `sbt --java-home` (sbt ignores $JAVA_HOME) + BLOOP_JAVA_HOME
#   - keep /etc/sbt/sbtopts (PKI mirror); scrub JAVA_TOOL_OPTIONS/JDK_JAVA_OPTIONS
#   - `bloop clean` before BOTH the raw run AND the rtk re-execution: rtk re-runs
#     the command (PLAN #19); a cached successful compile would otherwise report
#     "up-to-date" on the second run and silently drop all warnings (A/B is wrong).
#     Failing compiles and `test` re-execute regardless, but cleaning is harmless.
set -euo pipefail

RSX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JDK="${RSX_JAVA21:-$HOME/.local/share/mise/installs/java/21}"
RTK="${RTK_BIN:-$(cd "$RSX_ROOT/.." && pwd)/rtk/target/release/rtk}"
WORK="${RSX_REAL_WORK:-/tmp/rsx-real}"
FIX="$RSX_ROOT/fixtures/real/bloop"
CSV="$FIX/real_savings.csv"
# sbt-bloop plugin version baked into each repo's patches/setup.patch. Pinned to 2.0.19 = the
# box's GLOBAL plugin version: 2.1.0 breaks play's bloopInstall (`-release 11 not supported`),
# and 2.0.19 is what generated the original fixtures, so per-project output stays byte-identical.
# shellcheck disable=SC2034  # documentation constant; the value lives in the setup.patch files.
SBT_BLOOP_VER="2.0.19"
JDK17="${RSX_JAVA17:-$HOME/.local/share/mise/installs/java/17}"
# Per-repo JVM override (default = JDK 21). cats-effect pins Scala 3.2.2, whose compiler
# cannot read JDK-21 class files (dies with `class file java/lang/annotation/ElementType.class
# is broken, bad constant pool index`); on JDK 21 its bloopInstall also silently drops
# testsJVM-test.json (bloopGenerate's compile fails) so `bloop test` finds no suites. Both
# bloopInstall AND the bloop server/compile must run on JDK 17. Other repos stay on 21.
declare -A REPO_JDK=( [cats-effect]="$JDK17" )

# repo -> "url|tag|sha|scala_tag|test_project|compile_project|test_filter"
# enumeratum + cats-effect bloopInstall exits non-zero (mirror/codegen quirks) but writes
# usable JVM configs first — handled by bloop_install()'s tolerate-and-verify (see HEADER).
# play is the multimodule-large repo: compiling the Play-Netty-Server leaf cascades through
# Build-Link -> Exceptions -> Streams -> Play (core) -> Play-Server -> Play-Netty-Server, so a
# single `compile` yields the real per-module headers + warning storm (compile_warn / compile_error,
# on compile_project=Play-Netty-Server). test_project is the **Play core** module: `bloop test Play`
# runs 81 specs2 suites (~40s cold) — test_pass (no patch) and test_fail (assertion-fail.patch flips
# one PlayIOSpec assertion). The filter collapses test output to the summary line, so the dep-compile
# cascade that precedes it (cold on the raw run, warm on rtk's) is invisible in the A/B (no special
# CLEAN needed for tests, unlike the compile cascade which uses the CLEAN table below).
declare -A REPO=(
  [circe]="https://github.com/circe/circe.git|v0.14.10|400433e44cf8821caec34568e7f9e1384febf329|213|testsJVM|coreJVM|"
  [enumeratum]="https://github.com/lloydmeta/enumeratum.git|enumeratum-1.7.5|e3869a725786013d4725ea90f2ec81d84e661206|212|coreJVM|coreJVM|"
  [zio-json]="https://github.com/zio/zio-json.git|v0.7.3|2174436c4bed3470b37751a2ac8f7f2b7acee53e|213|zioJsonJVM|zioJsonJVM|"
  [cats-effect]="https://github.com/typelevel/cats-effect.git|v3.5.7|58a54e82f7655cc517a9e35d2d8b33ccaab1ca48|3|testsJVM|coreJVM|--only cats.effect.ExitCodeSpec"
  [play]="https://github.com/playframework/playframework.git|3.0.11|25ebb696b69ca09f7560878fe1512a777aab154e|3|Play|Play-Netty-Server|"
)
# Optional per-repo clean target (defaults to the compile/test project). bloop compiles a
# project's out-of-date dependencies, but `clean <leaf>` only cleans the leaf — so on the rtk
# re-run the warm upstream wouldn't recompile and the cascade would vanish (invalid A/B, PLAN
# #19). For Play we clean the whole dependency chain so BOTH runs emit the full cold cascade.
declare -A CLEAN=(
  [play]="Play-Build-Link Play-Exceptions Play-Streams Play Play-Server Play-Netty-Server"
)
# Per-repo prep is ENCODED in bloop_install() below (tolerate-and-verify), not done by hand:
#   enumeratum  : bloopInstall exits 1 (enumeratum-play-json:1.8.3-SNAPSHOT not mirrored) but
#                 writes coreJVM configs first (tolerated; verified). sbt-doctest's generated
#                 test sources are then deleted so a direct `bloop` run won't compile them.
#                 Default Scala 2.12.18. No warn fixture (core compiles clean).
#   cats-effect : default Scala 2.13 bloopInstall fails on a scala-library eviction, so we build
#                 under Scala 3 (`++3.2.2 bloopInstall`); that export fails on the scala-native
#                 'clang' check but writes the JVM configs first (tolerated; verified). Tests are
#                 scoped to ExitCodeSpec via the REPO test_filter field (`--only …`, forwarded to
#                 bloop by capture()) to stay fast + deterministic. No warn fixture.

die() { echo "capture-real: $*" >&2; exit 1; }

pin_env() {
  [ -x "$JDK/bin/java" ]  || die "JDK not found at $JDK"
  # Must be a full JDK, not a JRE: bloop's in-process javac needs lib/ct.sym for `--release`
  # cross-compilation (play targets `--release 11`). A JRE silently yields `release version 11
  # not supported` + `java.lang.Object not found` only for repos that set --release (e.g. play),
  # so guard up front. (/usr/lib/jvm/java-21-openjdk is a JRE here; use the mise full JDK.)
  [ -x "$JDK/bin/javac" ] || die "not a full JDK (no javac) at $JDK — point RSX_JAVA21 at a JDK"
  [ -f "$JDK/lib/ct.sym" ] || die "JDK at $JDK has no lib/ct.sym — --release cross-compile will fail"
  # Scrub inherited env that alters child output so the capture is controlled solely by this
  # script: BASH_ENV (the sandbox's bashenv.sh force-exports NO_COLOR/FORCE_COLOR into every
  # non-interactive subshell), any inherited SBT_OPTS, and the JVM *_OPTIONS launchers. We set
  # NO_COLOR ourselves for the nocolor corpus; /etc/sbt/sbtopts (PKI mirror) is a file, kept.
  unset BASH_ENV SBT_OPTS FORCE_COLOR JAVA_TOOL_OPTIONS JDK_JAVA_OPTIONS 2>/dev/null || true
  export JAVA_HOME="$JDK" BLOOP_JAVA_HOME="$JDK" NO_COLOR=1 COLUMNS=100
}

# Apply the repo's committed build setup (patches/setup.patch: per-project sbt-bloop plugin so
# we don't rely on the box's global plugin, sbt-version fixes, etc.) and COMMIT it into the
# clone, making it the clone's baseline. capture()'s per-situation `git checkout -- .` then
# reverts to THIS commit (setup intact) and only drops the failure patch — which is why
# build.properties no longer regresses to the broken value between situations. Idempotent.
apply_setup() {
  local repo="$1" dir="$2"; local patch="$RSX_ROOT/real/$repo/patches/setup.patch"
  [ -f "$patch" ] || return 0
  [ "$(git -C "$dir" log -1 --format=%s 2>/dev/null)" = "rtk: setup" ] && return 0
  git -C "$dir" apply "$patch" || die "setup.patch apply failed for $repo"
  git -C "$dir" -c user.email=rtk@local -c user.name=rtk commit -aqm "rtk: setup" \
    || die "setup commit failed for $repo"
}

# bloopInstall with per-repo prep. enumeratum + cats-effect bloopInstall *expectedly*
# exit non-zero (unmirrored SNAPSHOT / scala-native clang probe) but write the JVM
# configs we need first. Rather than `|| die` (which can't run those repos) or a
# comment telling a future agent to do it by hand, we tolerate the known failure and
# then ASSERT the configs we depend on actually exist — self-checking: if the mirror
# shifts and the configs stop being produced, this fails loudly with a precise message.
bloop_install() {
  local repo="$1" dir="$2" tproj="$3" cproj="$4"
  ( cd "$dir"
    case "$repo" in
      cats-effect)  # default-2.13 dies on a scala-library eviction; build under Scala 3.
        sbt --java-home "$JDK" -batch "++3.2.2" bloopInstall >/dev/null 2>&1 || true ;;
      enumeratum)   # exits 1 (enumeratum-play-json:1.8.3-SNAPSHOT unmirrored), writes coreJVM first.
        sbt --java-home "$JDK" -batch bloopInstall >/dev/null 2>&1 || true ;;
      *)
        sbt --java-home "$JDK" -batch bloopInstall >/dev/null 2>&1 || die "bloopInstall $repo failed" ;;
    esac )
  # the tolerated failures above must STILL have produced these — else the assumption broke.
  local p; for p in "$tproj" "$cproj"; do
    [ -f "$dir/.bloop/$p.json" ] || die "bloopInstall $repo: missing .bloop/$p.json (mirror/prep changed?)"
  done
  # mechanical post-prep
  case "$repo" in
    enumeratum)  # sbt-doctest still emits *Doctest.scala test sources under src_managed/test that
                 # don't compile on Scala 2.12 (`Missing closing brace`) — delete them so
                 # `bloop test coreJVM` compiles. bloop never re-runs sbt generators, so deleting
                 # once post-bloopInstall is enough; src_managed is gitignored (survives revert).
      find "$dir" -path '*src_managed/test*' -name '*Doctest.scala' -delete 2>/dev/null || true ;;
  esac
  bloop exit >/dev/null 2>&1 || true   # bounce server onto this repo's JDK ($JDK)
}

ensure_clone() {  # repo -> stages $WORK/<repo>, tweaks, bloopInstall (idempotent)
  local repo="$1" url tag sha sver tproj cproj tfilter dir
  IFS='|' read -r url tag sha sver tproj cproj tfilter <<<"${REPO[$repo]}"
  dir="$WORK/$repo"
  if [ ! -d "$dir/.git" ]; then
    mkdir -p "$WORK"
    git clone --depth 1 --branch "$tag" "$url" "$dir" >/dev/null 2>&1 || die "clone $repo failed"
    [ "$(git -C "$dir" rev-parse HEAD)" = "$sha" ] || echo "capture-real: WARN $repo HEAD != pinned $sha" >&2
  fi
  apply_setup "$repo" "$dir"             # idempotent — commits setup.patch into the clone once
  [ -d "$dir/.bloop" ] || bloop_install "$repo" "$dir" "$tproj" "$cproj"
  echo "$dir"
}

# capture <name> <dir> <project> <bloop-subcmd: test|compile> [patch-file] [extra-bloop-args]
# extra-bloop-args (e.g. "--only cats.effect.ExitCodeSpec") is word-split into BOTH the raw
# and rtk runs, so the A/B stays apples-to-apples (rtk forwards trailing args to bloop).
capture() {
  local name="$1" dir="$2" proj="$3" cmd="$4" patch="${5:-}" xargs="${6:-}" xclean="${7:-$3}"
  ( cd "$dir"
    [ -n "$patch" ] && { git apply "$patch" || die "patch apply failed: $patch"; }
    bloop clean $xclean >/dev/null 2>&1
    bloop "$cmd" "$proj" $xargs > "$FIX/$name.txt" 2>&1 || true  # raw (non-zero on fail/error is expected)
    bloop clean $xclean >/dev/null 2>&1                          # clean again before rtk re-execution
    "$RTK" bloop "$cmd" "$proj" $xargs > "$FIX/$name.rtk.txt" 2>/dev/null || true
    [ -n "$patch" ] && git checkout -- . 2>/dev/null || true     # revert so next situation is clean
  )
  savings_row "$name"
  echo "  captured $name  ($(wc -l <"$FIX/$name.txt") raw lines -> $(wc -w <"$FIX/$name.rtk.txt") filtered tokens)"
}

savings_row() {
  local name="$1" raw="$FIX/$1.txt" flt="$FIX/$1.rtk.txt" rb rt fb ft saved
  grep -v "^${name}," "$CSV" > "$CSV.tmp" 2>/dev/null && mv "$CSV.tmp" "$CSV" || true
  rb=$(wc -c <"$raw"); rt=$(wc -w <"$raw"); fb=$(wc -c <"$flt"); ft=$(wc -w <"$flt")
  if [ "$rt" -gt 0 ]; then saved=$(awk "BEGIN{printf \"%.1f\",(1-$ft/$rt)*100}"); else saved=0; fi
  printf '%s,%s,%s,%s,%s,%s\n' "$name" "$rb" "$rt" "$fb" "$ft" "$saved" >> "$CSV"
}

main() {
  local repo="${1:-}" sit="${2:-all}"
  [ -n "${REPO[$repo]:-}" ] || die "unknown repo: $repo (have: ${!REPO[*]})"
  JDK="${REPO_JDK[$repo]:-$JDK}"   # per-repo JVM (cats-effect -> JDK 17); drives pin_env, sbt, server
  pin_env
  local url tag sha sver tproj cproj tfilter
  IFS='|' read -r url tag sha sver tproj cproj tfilter <<<"${REPO[$repo]}"
  local cclean="${CLEAN[$repo]:-$cproj}"   # whole dep chain for Play, else just the project
  [ -f "$CSV" ] || printf 'fixture,raw_bytes,raw_tokens,filtered_bytes,filtered_tokens,pct_saved\n' > "$CSV"
  local dir; dir="$(ensure_clone "$repo")"
  local pdir="$RSX_ROOT/real/$repo/patches"
  run_one() { case "$1" in
    test_pass)     capture "real_${repo}_test_pass_${sver}"     "$dir" "$tproj" test    ""                          "$tfilter" ;;
    test_fail)     capture "real_${repo}_test_fail_${sver}"     "$dir" "$tproj" test    "$pdir/assertion-fail.patch" "$tfilter" ;;
    test_error)    capture "real_${repo}_test_error_${sver}"    "$dir" "$tproj" test    "$pdir/error.patch"          "$tfilter" ;;
    compile_pass)  capture "real_${repo}_compile_pass_${sver}"  "$dir" "$cproj" compile ""                          "" "$cclean" ;;
    compile_error) capture "real_${repo}_compile_error_${sver}" "$dir" "$cproj" compile "$pdir/compile-error.patch" "" "$cclean" ;;
    compile_warn)  capture "real_${repo}_compile_warn_${sver}"  "$dir" "$cproj" compile ""                          "" "$cclean" ;;
    *) die "unknown situation: $1" ;; esac; }
  if [ "$sit" = all ]; then
    for s in test_pass test_fail test_error compile_error compile_warn; do run_one "$s"; done
  else run_one "$sit"; fi
  echo "done: $repo / $sit"
}
main "$@"
