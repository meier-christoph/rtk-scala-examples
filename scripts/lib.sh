# Shared helpers for the rtk-scala-examples capture pipeline. Source only (no shebang).
#
# Encodes the verified Phase-0 rig facts (see PLAN §7 and the project memory):
#   - sbt ignores $JAVA_HOME; the JVM lever is `sbt --java-home <path>` (so the
#     exported .bloop platform.config.home = JDK 21, not the box-default 25).
#   - /tmp/workspace must be a REAL directory copy, not a symlink: the JVM
#     canonicalizes a symlinked cwd back to $HOME (leaks the home path).
#   - keep /etc/sbt/sbtopts (PKI mirror); do NOT inherit JAVA_TOOL_OPTIONS/JDK_JAVA_OPTIONS.

# Resolve the mise JDK 21 install (e.g. .../java/21.50.15.0 via the `21` symlink).
RSX_JAVA21="${RSX_JAVA21:-$HOME/.local/share/mise/installs/java/21}"
RSX_WORKSPACE_ROOT="${RSX_WORKSPACE_ROOT:-/tmp/workspace}"

rsx_die() { printf 'capture: %s\n' "$*" >&2; exit 1; }
rsx_info() { printf 'capture: %s\n' "$*" >&2; }

# rsx_pin_env <color|nocolor>
# Sets an explicit, reproducible environment (PLAN §3 #20/#21). Exports for the caller.
rsx_pin_env() {
  local mode="${1:-nocolor}"
  [ -x "$RSX_JAVA21/bin/java" ] || rsx_die "JDK 21 not found at $RSX_JAVA21"
  export JAVA_HOME="$RSX_JAVA21"          # for tools that honor it (bloop wrapper does)
  export BLOOP_JAVA_HOME="$RSX_JAVA21"    # bloop server/client JVM
  unset JAVA_TOOL_OPTIONS JDK_JAVA_OPTIONS 2>/dev/null || true
  export COLUMNS=100                      # pin width so any wrapping is stable
  case "$mode" in
    nocolor)
      export NO_COLOR=1
      export SBT_OPTS="-Dsbt.log.noformat=true -Djline.terminal=none" ;;
    color)
      unset NO_COLOR NO_COLORS 2>/dev/null || true
      export SBT_OPTS="" ;;
    *) rsx_die "unknown color mode: $mode" ;;
  esac
}

# rsx_stage_workspace <repo-name> -> echoes the staged absolute path
# Copies repos/<name> to /tmp/workspace/<name> as a real directory (no symlink),
# so all rendered paths read /tmp/workspace/... and never $HOME.
rsx_stage_workspace() {
  local name="$1" src dst
  src="$RSX_ROOT/repos/$name"
  [ -d "$src" ] || rsx_die "repo not found: $src (run generator/gen.py first)"
  dst="$RSX_WORKSPACE_ROOT/$name"
  rm -rf "$dst"
  mkdir -p "$RSX_WORKSPACE_ROOT"
  cp -a "$src/." "$dst/"
  echo "$dst"
}

# rsx_bloop_install <workspace-dir>
# Exports bloop config with the JDK-21 platform home. Must pass --java-home: sbt
# does not honor $JAVA_HOME.
rsx_bloop_install() {
  local ws="$1"
  ( cd "$ws" && sbt --java-home "$RSX_JAVA21" -batch -no-colors bloopInstall ) >/dev/null 2>&1 \
    || rsx_die "bloopInstall failed in $ws"
}

# rsx_bloop_restart — bounce the long-lived server so it runs under the pinned JDK.
rsx_bloop_restart() {
  bloop exit >/dev/null 2>&1 || true
}

# rsx_token_count <file> — whitespace-split token proxy (matches rtk's savings asserts).
rsx_token_count() {
  wc -w <"$1" | tr -d ' '
}

# rsx_savings_row <savings.csv> <fixture> <raw-file> <filtered-file-or-empty>
# Upserts a row (replaces any existing row for <fixture> so re-runs stay clean).
# Records bytes/tokens raw-vs-filtered + %saved. Filtered empty => "skipped".
rsx_savings_row() {
  local csv="$1" fixture="$2" raw="$3" filtered="${4:-}"
  local rb rt fb ft saved
  # drop any prior row for this fixture (idempotent pipeline)
  if [ -f "$csv" ]; then
    grep -v "^${fixture}," "$csv" >"$csv.tmp" 2>/dev/null || true
    mv "$csv.tmp" "$csv"
  fi
  rb=$(wc -c <"$raw" | tr -d ' '); rt=$(rsx_token_count "$raw")
  if [ -n "$filtered" ] && [ -s "$filtered" ]; then
    fb=$(wc -c <"$filtered" | tr -d ' '); ft=$(rsx_token_count "$filtered")
    if [ "$rt" -gt 0 ]; then saved=$(awk "BEGIN{printf \"%.1f\", (1-$ft/$rt)*100}"); else saved="0.0"; fi
  else
    fb=""; ft=""; saved="skipped"
  fi
  printf '%s,%s,%s,%s,%s,%s\n' "$fixture" "$rb" "$rt" "$fb" "$ft" "$saved" >>"$csv"
}

# rsx_init_savings <savings.csv> — write header if file is absent.
rsx_init_savings() {
  local csv="$1"
  [ -f "$csv" ] || printf 'fixture,raw_bytes,raw_tokens,filtered_bytes,filtered_tokens,pct_saved\n' >"$csv"
}
