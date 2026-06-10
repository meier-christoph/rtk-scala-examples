# real/ — real-world repo capture track (local-only)

Captured **real** Scala build/test output from well-known ecosystem repos, to validate
rtk's bloop filter against output the *generated* rig (`generator/`, `repos/`) can't
synthesize — real suite names, real warning storms, real volume, deep real diagnostics.

**Local-only** (like PLAN Phase 4): not intended to ship upstream into rtk. Kept strictly
separate from the generated pipeline — different fixtures dir (`fixtures/real/bloop/`,
not `fixtures/bloop/`), different `real_*` filename prefix, its own `real_savings.csv`.

## Method

We do **not** commit or mirror the repo trees. For each repo we pin a tag+SHA, apply one
minimal build tweak (add the sbt-bloop plugin; bump sbt where an old pin fatals on JDK 21),
and commit only the small **failure patches** (`<repo>/patches/*.patch`) + the captured
output. `capture-real.sh <repo> <situation>` reproduces everything: shallow-clone @ tag →
tweak → `bloopInstall` (mirror) → `bloop clean` → [apply patch] → `bloop test|compile` →
raw `.txt`; then **clean again** → rtk re-run → `.rtk.txt` (PLAN #19: rtk re-executes, so a
cached successful compile would report "up-to-date" on the 2nd run and drop all warnings —
clean before *both* runs). Default Scala version per repo (adds 2.13 output the generated
Scala-3-only set lacks). Captured once & frozen (PLAN #6); not bit-reproducible.

The per-repo prep that *isn't* uniform is **encoded, not left to a future agent's hands**:
`bloop_install()` tolerates the bloopInstall exits that are expected-but-still-produce-configs
(enumeratum's unmirrored play-json SNAPSHOT; cats-effect's `++3.2.2` scala-native clang probe),
then **asserts** the `.bloop/<proj>.json` it needs actually exists — so it fails loudly if the
mirror shifts rather than silently capturing nothing. `tweak_build` runs on every invocation
(idempotent), so a pre-staged clone is fixed up too. Test scoping (cats-effect `--only
ExitCodeSpec`) and the Play clean-chain are data in the `REPO`/`CLEAN` tables, forwarded by
`capture()` to both the raw and rtk runs.

> **Path rendering.** Clones live under `$RSX_REAL_WORK` (default `/tmp/rsx-real`), so a raw
> fixture may show that deterministic `/tmp` path — analogous to the generated rig's accepted
> `/tmp/workspace/...` (PLAN §9.2), never `$HOME`. Most frameworks print repo-relative paths;
> **zio-test is the exception** — its defect stack frames carry the absolute source path
> (`at /tmp/rsx-real/zio-json/.../EncoderSpec.scala:27` in `real_zio-json_test_error_213.txt`).
> The rtk filter shortens it to `(EncoderSpec.scala:27)`, so the consumer-facing `.rtk.txt` is
> clean. Left as-is (zero post-processing, PLAN #6); it's authentic real filter input.

## Provenance (pinned)

| Repo | Tag | SHA | Scala | Framework | Build tweak | test proj / compile proj | License |
|------|-----|-----|-------|-----------|-------------|--------------------------|---------|
| circe | v0.14.10 | 400433e | 2.13.14 | munit + discipline | +sbt-bloop | `testsJVM` / `coreJVM` | Apache-2.0 |
| enumeratum | enumeratum-1.7.5 | e3869a7 | 2.12.18 | scalatest + scalacheck | +sbt-bloop; del doctest gen sources | `coreJVM` / `coreJVM` | MIT |
| zio-json | v0.7.3 | 2174436 | 2.13.13 | zio-test | +sbt-bloop | `zioJsonJVM` / `zioJsonJVM` | Apache-2.0 |
| cats-effect | v3.5.7 | 58a54e8 | 3.2.2 | specs2 + discipline | +sbt-bloop, sbt→1.10.7, build `++3.2.2` | `testsJVM` (`--only ExitCodeSpec`) / `coreJVM` | Apache-2.0 |
| play | 3.0.11 | 25ebb69 | 3.3.7 | specs2 (Play) + JUnit | +sbt-bloop | `Play` / `Play-Netty-Server` (cascade) | Apache-2.0 |

**Coverage: 22 fixtures.** circe (5: pass/fail/**error**/compile_error/compile_warn), zio-json (5),
enumeratum (4: no warn — core compiles clean), cats-effect (4: no warn — fatal-warnings clean),
**play (4: compile_warn/compile_error — the multimodule-large cascade — plus test_pass/test_fail —
the large mixed-framework test run)**.
Distinct compile-error kind per repo (circe *missing implicit* · enumeratum *not found: value*
· zio-json *not a member* · cats-effect *overrides nothing* · **play *overloaded method cannot
be applied***); distinct uncaught-exception (`error`) shape per framework (circe munit
*NoSuchElementException* · zio-json zio-test *defect* · enumeratum scalatest *NoSuchElementException*
· cats-effect specs2 *`!` errored example*); four Scala versions (2.12/2.13/3); four test
frameworks. See `fixtures/real/bloop/real_savings.csv` for token savings.

## Situations (per repo)

- `test_pass` — clean run of the test project (real large green output).
- `test_fail` — `assertion-fail.patch` flips one real assertion → one failure among many passes.
- `test_error` — `error.patch` makes one test throw an **uncaught exception** (not an assertion):
  the real per-framework `error` shape (munit/scalatest stack frame, zio-test defect bullet,
  specs2 `!` errored example). Exercises the J/K/L + munit-error filter fixes on real output.
- `compile_error` — `compile-error.patch` injects a type error in a core source.
- `compile_warn` — clean compile of a warning-emitting module (no patch).
- **`compile_pass`** — clean compile, no warnings (situation exists; no repo currently uses it).

**Play (multimodule-large):** compiling the `Play-Netty-Server` leaf cascades through
Build-Link → Exceptions → Streams → Play (core) → Play-Server → Play-Netty-Server, so a single
`bloop compile` emits the real per-module `Compiling X (N Scala + M Java sources)` headers,
parallel interleaving, and a 27-warning storm — the multimodule shape the synthetic `mm` rig
can't produce. `compile_error` injects the error in the upstream `Play-Server`, so the cascade
compiles core (with warnings) then fails at `Play-Server` (5 of 6 projects reached). The whole
dependency chain is cleaned before both the raw and rtk runs (see `CLEAN` in `capture-real.sh`)
so the cold cascade is identical on both sides of the A/B.

Play also carries the two **test** situations on its `Play` core module (`bloop test Play`): a real
**mixed-framework** run — 81 suites / 1192 tests across specs2 **and** JUnit (Java) — that the
synthetic single-framework rig can't produce. `test_pass` is the unpatched green run; `test_fail`
flips one assertion in `PlayIOSpec` (`assertion-fail.patch`). The dep-compile cascade that precedes
the test run is collapsed away by the filter (it's cold on the raw run, warm on rtk's), so no special
`CLEAN` is needed for the test side — only the compile cascade uses the `CLEAN` table.

## Findings surfaced

See `../FINDINGS.md` (section **🆕 REAL-*** entries). The real captures exposed **three HIGH
gaps the generated set never hit**, all in the bloop filter's per-framework failure extraction:
- **REAL-1** munit multi-line `ComparisonFailException` (nested ADT diff) — `=> Obtained`
  block + diff body dropped, only the `=> Diff` header kept. (`real_circe_test_fail_213`)
- **REAL-2** scalatest `FunSpec` (describe/it nesting) — 1 real failure filtered into **4**
  `[FAIL]`s; passing `-`-prefixed lines mis-detected. (`real_enumeratum_test_fail_212`)
- **REAL-4** specs2 with marker **and** reason on stderr — filter expects the `x` marker on
  stdout, so it emits `1 failed` with an **empty** body. (`real_cats-effect_test_fail_3`)

Hand these to the filter author (`../rtk-bloop` — the latest bloop filter; all captures here
use its locally-built binary, since the sbt side in `../rtk` is not yet live).

**`test_error` + Play additions (2026-06-08) — validation, no new gaps.** The four uncaught-
exception fixtures confirm the J/K/L + munit-`error` filter fixes hold on *real* output across all
four frameworks (munit `NoSuchElementException` + user frame; zio-test defect bullet; scalatest
`*** FAILED ***` exception; specs2 `!` errored example) — 72–99.8% saved. Play's two compile
fixtures confirm the **multimodule** handling generalizes from the synthetic 2-module `mm` rig to
a real 6-module cascade: the header aggregates `354 sources, 27 warnings (6 projects)` /
`347 sources, 1 error, 25 warnings (5 projects)` across interleaved parallel module output
(finding G), composes error+warning counts (REAL-3), and sums mixed Scala+Java sources (REAL-5) —
83–96% saved. None surfaced a new filter gap.

**Play test run (2026-06-09) — validation, no new gaps.** Two test fixtures were added on the
`Play` core module (`bloop test Play`): a real **mixed-framework** run interleaving specs2 and JUnit
output across 81 suites / 1192 tests. `test_pass` collapses to `bloop test: 1192 passed (81 suites,
23.0s)` (100% saved); `test_fail` flips one `PlayIOSpec` assertion → `bloop test: 1191 passed, 1
failed` + `[FAIL] read file content` / `'file content' != 'rtk injected failure' (PlayIOSpec.scala:21)`
(99.8% saved). Confirms the tally aggregation + specs2 failure extraction hold when JUnit `Test run …
finished: N failed` lines are interleaved with specs2 markers on a large real run — no new gap.
