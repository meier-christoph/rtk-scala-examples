#!/usr/bin/env python3
"""rtk-scala-examples generator.

Writes one self-contained, *real* Scala project frozen in a single situation at a
single scale (and topology). Idempotent: re-running regenerates the repo's sources;
target/ .bloop/ .bsp/ are gitignored and left untouched.

Deterministic by construction (no randomness). Source is written in **brace style**
that compiles on BOTH Scala 2.13 and 3 so cross-version capture can dedup (PLAN #4).

Each repo gets a committed `.rsx-meta` file recording the canonical fields, so the
capture pipeline reads structured data instead of parsing directory names.

(Python rather than the original Bash: the Phase-3 work is ~19 styles of
escaping-hostile Scala source + a lib×style×situation matrix — templating + data,
which Python handles cleanly. The capture pipeline stays Bash: it's process
orchestration. The seam between them is the `.rsx-meta` contract.)

Usage (flag-driven — situations may contain underscores, so no positional parsing):
    gen.py --lib munit --style funsuite --situation fail --scale small [--topology single|mm]
    gen.py --situation compile_error --scale large        # agnostic (no --lib)
    gen.py --situation no_tests                           # agnostic, scale-less

Repo dir naming (PLAN §6, hyphens):
    single   : <lib>-<style>-<situation>-<scale>     e.g. munit-funsuite-fail-small
    multimod : mm-<lib>-<situation>-<scale>          e.g. mm-munit-fail-large
    agnostic : _<situation>-<scale>                  e.g. _compile-error-large, _no-tests
(situation underscores render as hyphens in dir names: compile_error -> compile-error)
"""

import argparse
import shutil
import sys
from pathlib import Path

import versions as V

ROOT = Path(__file__).resolve().parent.parent

# Situation classification ----------------------------------------------------
AGNOSTIC_SITUATIONS = {"warn", "compile_error", "compile_pass", "incremental", "no_tests"}
TEST_COMMAND_SITUATIONS = {"pass", "fail", "error", "warn_fail", "skipped", "no_tests"}
COMPILE_COMMAND_SITUATIONS = {"warn", "compile_error", "compile_pass", "incremental"}
SCALELESS_SITUATIONS = {"compile_pass", "incremental", "no_tests"}

MODULES = ("core", "util")


def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"gen: {msg}", file=sys.stderr)
    raise SystemExit(1)


# ============================================================================
#  source emitters (brace style, 2.13 + 3 compatible)
# ============================================================================
def main_file(variant: str, pkg: str = "example") -> str:
    """The main object. variant: clean | warn | error."""
    lines = [
        f"package {pkg}",
        "",
        "/** Structural dummy: reproduces output shape, not real domain logic. */",
        "object Calculator {",
        "  def add(a: Int, b: Int): Int = a + b",
        "  def sub(a: Int, b: Int): Int = a - b",
        "  def mul(a: Int, b: Int): Int = a * b",
        "  def div(a: Int, b: Int): Int = a / b",
    ]
    if variant == "warn":
        lines += [
            "",
            "  // non-exhaustive match on a sealed type (Option) -> 'match may not be",
            "  // exhaustive' warning, emitted by default on both 2.13 and 3 (no flags).",
            "  def label(o: Option[Int]): String = o match {",
            '    case Some(n) => "some " + n',
            "  }",
        ]
    elif variant == "error":
        lines += [
            "",
            "  // deliberate type error -> compilation fails",
            '  val broken: Int = "not an int"',
        ]
    lines.append("}")
    return "\n".join(lines) + "\n"


def munit_suite(cls: str, mode: str, pkg: str = "example") -> str:
    """A munit FunSuite. mode: pass | fail | error | skipped.

    The "div" line is the per-mode defect carrier; "sub" is a second defect for fail.
    """
    sub_name = "sub returns the difference"
    div_name = "div returns the quotient"

    sub_open = f'  test("{sub_name}".ignore) {{' if mode == "skipped" else f'  test("{sub_name}") {{'
    sub_body = "    assertEquals(Calculator.sub(10, 4), 7)" if mode == "fail" \
        else "    assertEquals(Calculator.sub(10, 4), 6)"

    div_open = f'  test("{div_name}".ignore) {{' if mode == "skipped" else f'  test("{div_name}") {{'
    if mode == "fail":
        div_body = "    assertEquals(Calculator.div(20, 4), 4)"   # 5 != 4 -> diff
    elif mode == "error":
        div_body = "    assertEquals(Calculator.div(20, 0), 5)"   # ArithmeticException -> error
    else:
        div_body = "    assertEquals(Calculator.div(20, 4), 5)"

    lines = [
        f"package {pkg}",
        "",
        f"class {cls} extends munit.FunSuite {{",
        "",
        '  test("add returns the sum") {',
        "    assertEquals(Calculator.add(2, 3), 5)",
        "  }",
        "",
        sub_open,
        sub_body,
        "  }",
        "",
        '  test("mul returns the product") {',
        "    assertEquals(Calculator.mul(6, 7), 42)",
        "  }",
        "",
        div_open,
        div_body,
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def scalatest_funsuite(cls: str, mode: str, pkg: str = "example") -> str:
    """ScalaTest AnyFunSuite. `assert(==)` yields ScalaTest's macro diagnostic."""
    sub = "Calculator.sub(10, 4) == 7" if mode == "fail" else "Calculator.sub(10, 4) == 6"
    if mode == "error":
        div = "Calculator.div(20, 0) == 5"   # / by zero throws -> errored test
    elif mode == "fail":
        div = "Calculator.div(20, 4) == 4"
    else:
        div = "Calculator.div(20, 4) == 5"
    lines = [
        f"package {pkg}",
        "",
        "import org.scalatest.funsuite.AnyFunSuite",
        "",
        f"class {cls} extends AnyFunSuite {{",
        "",
        '  test("add returns the sum") {',
        "    assert(Calculator.add(2, 3) == 5)",
        "  }",
        "",
        '  test("sub returns the difference") {',
        f"    assert({sub})",
        "  }",
        "",
        '  test("mul returns the product") {',
        "    assert(Calculator.mul(6, 7) == 42)",
        "  }",
        "",
        '  test("div returns the quotient") {',
        f"    assert({div})",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def _st_cases(mode: str):
    """(label, expr, expected) for the four calculator cases. sub & div fail in `fail`
    mode; in `error` mode the div case divides by zero (throws -> errored test, the
    add/sub/mul cases stay green) — mirrors munit_suite's error shape."""
    div_expr = "Calculator.div(20, 0)" if mode == "error" else "Calculator.div(20, 4)"
    return [
        ("add returns the sum", "Calculator.add(2, 3)", 5),
        ("sub returns the difference", "Calculator.sub(10, 4)", 7 if mode == "fail" else 6),
        ("mul returns the product", "Calculator.mul(6, 7)", 42),
        ("div returns the quotient", div_expr, 4 if mode == "fail" else 5),
    ]


def scalatest_flatspec(cls: str, mode: str, pkg: str = "example") -> str:
    c = _st_cases(mode)
    lines = [f"package {pkg}", "", "import org.scalatest.flatspec.AnyFlatSpec", "",
             f"class {cls} extends AnyFlatSpec {{", "",
             f'  "Calculator" should "{c[0][0]}" in {{', f"    assert({c[0][1]} == {c[0][2]})", "  }"]
    for label, expr, exp in c[1:]:
        lines += ["", f'  it should "{label}" in {{', f"    assert({expr} == {exp})", "  }"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def scalatest_funspec(cls: str, mode: str, pkg: str = "example") -> str:
    lines = [f"package {pkg}", "", "import org.scalatest.funspec.AnyFunSpec", "",
             f"class {cls} extends AnyFunSpec {{", '  describe("Calculator") {']
    for label, expr, exp in _st_cases(mode):
        lines += [f'    it("{label}") {{', f"      assert({expr} == {exp})", "    }"]
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def scalatest_wordspec(cls: str, mode: str, pkg: str = "example") -> str:
    lines = [f"package {pkg}", "", "import org.scalatest.wordspec.AnyWordSpec", "",
             f"class {cls} extends AnyWordSpec {{", '  "Calculator" should {']
    for label, expr, exp in _st_cases(mode):
        lines += [f'    "{label}" in {{', f"      assert({expr} == {exp})", "    }"]
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def scalatest_freespec(cls: str, mode: str, pkg: str = "example") -> str:
    lines = [f"package {pkg}", "", "import org.scalatest.freespec.AnyFreeSpec", "",
             f"class {cls} extends AnyFreeSpec {{", '  "Calculator" - {']
    for label, expr, exp in _st_cases(mode):
        lines += [f'    "{label}" in {{', f"      assert({expr} == {exp})", "    }"]
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def scalatest_propspec(cls: str, mode: str, pkg: str = "example") -> str:
    """PropSpec + TableDrivenPropertyChecks — a table of (a, b, expected-sum) rows;
    one row's expected sum is wrong in fail mode so forAll reports a failing row."""
    add_rows = [(2, 3, 5), (10, 7, 17 if mode != "fail" else 99), (6, 7, 13), (20, 4, 24)]
    tbl = ",\n      ".join(f"({a}, {b}, {s})" for a, b, s in add_rows)
    lines = [
        f"package {pkg}", "",
        "import org.scalatest.propspec.AnyPropSpec",
        "import org.scalatest.prop.TableDrivenPropertyChecks._", "",
        f"class {cls} extends AnyPropSpec {{",
        '  property("Calculator.add matches the table") {',
        '    val cases = Table(',
        '      ("a", "b", "sum"),',
        f"      {tbl}",
        "    )",
        "    forAll(cases) { (a: Int, b: Int, sum: Int) =>",
        "      assert(Calculator.add(a, b) == sum)",
        "    }",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def scalatest_featurespec(cls: str, mode: str, pkg: str = "example") -> str:
    """FeatureSpec with GivenWhenThen."""
    lines = [
        f"package {pkg}", "",
        "import org.scalatest.featurespec.AnyFeatureSpec",
        "import org.scalatest.GivenWhenThen", "",
        f"class {cls} extends AnyFeatureSpec with GivenWhenThen {{",
        '  Feature("Calculator arithmetic") {',
    ]
    for label, expr, exp in _st_cases(mode):
        lines += [
            f'    Scenario("{label}") {{',
            '      Given("two operands")',
            '      When("the operation runs")',
            f'      Then("the result is {exp}")',
            f"      assert({expr} == {exp})",
            "    }",
        ]
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def scalatest_refspec(cls: str, mode: str, pkg: str = "example") -> str:
    """RefSpec — test names are (backtick) methods."""
    lines = [f"package {pkg}", "", "import org.scalatest.refspec.RefSpec", "",
             f"class {cls} extends RefSpec {{"]
    for label, expr, exp in _st_cases(mode):
        lines += [f"  def `{label}`(): Unit = assert({expr} == {exp})"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def scalatest_matchers(cls: str, mode: str, pkg: str = "example") -> str:
    """FunSuite + should Matchers — the verbose 'X was not equal to Y' failure render."""
    lines = [f"package {pkg}", "",
             "import org.scalatest.funsuite.AnyFunSuite",
             "import org.scalatest.matchers.should.Matchers", "",
             f"class {cls} extends AnyFunSuite with Matchers {{"]
    for label, expr, exp in _st_cases(mode):
        lines += ["", f'  test("{label}") {{', f"    {expr} shouldBe {exp}", "  }"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def specs2_mutable(cls: str, mode: str, pkg: str = "example") -> str:
    """specs2 mutable.Specification.

    Uses `must beEqualTo(...)`: the implicit shorthands (`must_==`, `mustEqual`,
    `must_===`) do not resolve in specs2 5.x on Scala 3 (§9.3, verified).
    """
    sub = "Calculator.sub(10, 4) must beEqualTo(7)" if mode == "fail" else "Calculator.sub(10, 4) must beEqualTo(6)"
    if mode == "error":
        div = "Calculator.div(20, 0) must beEqualTo(5)"   # / by zero throws -> errored example
    elif mode == "fail":
        div = "Calculator.div(20, 4) must beEqualTo(4)"
    else:
        div = "Calculator.div(20, 4) must beEqualTo(5)"
    lines = [
        f"package {pkg}",
        "",
        "import org.specs2.mutable.Specification",
        "",
        f"class {cls} extends Specification {{",
        '  "Calculator" should {',
        '    "add returns the sum" in {',
        "      Calculator.add(2, 3) must beEqualTo(5)",
        "    }",
        '    "sub returns the difference" in {',
        f"      {sub}",
        "    }",
        '    "mul returns the product" in {',
        "      Calculator.mul(6, 7) must beEqualTo(42)",
        "    }",
        '    "div returns the quotient" in {',
        f"      {div}",
        "    }",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def ziotest_asserttrue(cls: str, mode: str, pkg: str = "example") -> str:
    """zio-test ZIOSpecDefault with assertTrue.

    Each case binds a local `result` first: assertTrue's failure diagnostic prints
    every sub-expression's value, and referencing the `Calculator` singleton directly
    would print its identity hashcode (`example.Calculator$@<hash>`) — non-deterministic.
    Binding to a local keeps the diagnostic to the computed value (§determinism).
    `@@ TestAspect.sequential` pins case order: zio-test runs cases concurrently by
    default, so the failure-report order would otherwise vary run-to-run.
    """
    cases = _zt_cases(mode)
    lines = [
        f"package {pkg}",
        "",
        "import zio.test._",
        "",
        f"object {cls} extends ZIOSpecDefault {{",
        '  def spec = suite("Calculator")(',
    ]
    for i, (name, expr, expected) in enumerate(cases):
        comma = "," if i < len(cases) - 1 else ""
        lines += [
            f'    test("{name}") {{',
            f"      val result = {expr}",
            f"      assertTrue(result == {expected})",
            f"    }}{comma}",
        ]
    lines += ["  ) @@ TestAspect.sequential", "}"]
    return "\n".join(lines) + "\n"


def _zt_cases(mode: str):
    """(name, expr, expected) for zio-test. sub & div fail in `fail` mode; in `error`
    mode the div case divides by zero so the bound `result` throws -> the test dies with
    a defect (the errored shape)."""
    div_expr = "Calculator.div(20, 0)" if mode == "error" else "Calculator.div(20, 4)"
    return [
        ("add returns the sum", "Calculator.add(2, 3)", "5"),
        ("sub returns the difference", "Calculator.sub(10, 4)", "7" if mode == "fail" else "6"),
        ("mul returns the product", "Calculator.mul(6, 7)", "42"),
        ("div returns the quotient", div_expr, "4" if mode == "fail" else "5"),
    ]


def ziotest_assertion(cls: str, mode: str, pkg: str = "example") -> str:
    """zio-test with the classic `assert(value)(Assertion.equalTo(...))` form (vs the
    `assertTrue` macro). The value is an eagerly-computed Int, so the diagnostic prints
    the value (no singleton-hashcode issue)."""
    lines = [
        f"package {pkg}", "", "import zio.test._", "",
        f"object {cls} extends ZIOSpecDefault {{", '  def spec = suite("Calculator")(',
    ]
    cases = _zt_cases(mode)
    for i, (name, expr, exp) in enumerate(cases):
        comma = "," if i < len(cases) - 1 else ""
        lines += [f'    test("{name}") {{',
                  f"      assert({expr})(Assertion.equalTo({exp}))",
                  f"    }}{comma}"]
    lines += ["  ) @@ TestAspect.sequential", "}"]
    return "\n".join(lines) + "\n"


def ziotest_nested(cls: str, mode: str, pkg: str = "example") -> str:
    """zio-test with nested `suite`s (a suite of suites). Binds a local `result` per
    case (determinism, see asserttrue) and pins sequential order."""
    cases = _zt_cases(mode)
    groups = [("additive", cases[0:2]), ("multiplicative", cases[2:4])]
    lines = [
        f"package {pkg}", "", "import zio.test._", "",
        f"object {cls} extends ZIOSpecDefault {{", '  def spec = suite("Calculator")(',
    ]
    for gi, (gname, gcases) in enumerate(groups):
        gcomma = "," if gi < len(groups) - 1 else ""
        lines.append(f'    suite("{gname}")(')
        for i, (name, expr, exp) in enumerate(gcases):
            comma = "," if i < len(gcases) - 1 else ""
            lines += [f'      test("{name}") {{',
                      f"        val result = {expr}",
                      f"        assertTrue(result == {exp})",
                      f"      }}{comma}"]
        lines.append(f"    ){gcomma}")
    lines += ["  ) @@ TestAspect.sequential", "}"]
    return "\n".join(lines) + "\n"


def ziotest_effectful(cls: str, mode: str, pkg: str = "example") -> str:
    """zio-test where each case is an effect (for-comprehension yielding the assertion)
    — the common real-world shape. The value flows through `ZIO.succeed`."""
    lines = [
        f"package {pkg}", "", "import zio._", "import zio.test._", "",
        f"object {cls} extends ZIOSpecDefault {{", '  def spec = suite("Calculator")(',
    ]
    cases = _zt_cases(mode)
    for i, (name, expr, exp) in enumerate(cases):
        comma = "," if i < len(cases) - 1 else ""
        lines += [f'    test("{name}") {{',
                  "      for {",
                  f"        result <- ZIO.succeed({expr})",
                  f"      }} yield assertTrue(result == {exp})",
                  f"    }}{comma}"]
    lines += ["  ) @@ TestAspect.sequential", "}"]
    return "\n".join(lines) + "\n"


def munit_clue(cls: str, mode: str, pkg: str = "example") -> str:
    """munit FunSuite with `assert(clue(x) == clue(y))` — the clue-annotated boolean
    assertion. On failure munit prints each clue's value, a different render from the
    `assertEquals` unified diff."""
    lines = [f"package {pkg}", "", f"class {cls} extends munit.FunSuite {{"]
    for label, expr, exp in _st_cases(mode):
        lines += ["", f'  test("{label}") {{',
                  f"    assert(clue({expr}) == clue({exp}))", "  }"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def munit_scalacheck(cls: str, mode: str, pkg: str = "example") -> str:
    """munit ScalaCheckSuite — property-based. Needs the munit-scalacheck dep (carried
    as a per-style dep in the registry).

    The failing property is false for *every* input, so ScalaCheck shrinks to the
    minimal counterexample (0) deterministically; the pinned initial seed additionally
    fixes the pre-shrink reporting (the `Failing seed:` line and `ARG_0_ORIGINAL`) so
    the output is byte-stable run-to-run (PLAN §0).

    NB: the lever is munit's `scalaCheckInitialSeed` (a base64 String), NOT
    `scalaCheckTestParameters.withInitialSeed` — munit derives the per-test seed from
    the former and overwrites the latter, so only this pins the reported seed."""
    rhs = "(n + 1)" if mode == "fail" else "n"   # fail: off-by-one, false for all n
    lines = [
        f"package {pkg}",
        "",
        "import org.scalacheck.Prop.forAll",
        "",
        f"class {cls} extends munit.ScalaCheckSuite {{",
        "",
        "  override def scalaCheckInitialSeed =",
        '    "TO7zgUWdv-WPJuetViT8r85tY3TprSjGhdyoESCTTkI="',
        "",
        '  property("add is commutative") {',
        "    forAll { (a: Int, b: Int) =>",
        "      Calculator.add(a, b) == Calculator.add(b, a)",
        "    }",
        "  }",
        "",
        '  property("add zero is identity") {',
        "    forAll { (n: Int) =>",
        f"      Calculator.add(n, 0) == {rhs}",
        "    }",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def specs2_acceptance(cls: str, mode: str, pkg: str = "example") -> str:
    """specs2 acceptance Specification — `def is = s2"..."` with example methods
    referenced by `$name` fragments. Uses `must beEqualTo` (the shorthands don't
    resolve on Scala 3, §9.3)."""
    names = ["add", "sub", "mul", "div"]
    cases = list(zip(names, _st_cases(mode)))
    frags = "\n".join(f"    {label} ${nm}" for nm, (label, _, _) in cases)
    defs = "\n".join(f"  def {nm} = {expr} must beEqualTo({exp})"
                     for nm, (_, expr, exp) in cases)
    lines = [
        f"package {pkg}",
        "",
        "import org.specs2.Specification",
        "",
        f'class {cls} extends Specification {{ def is = s2"""',
        "  Calculator should",
        frags,
        '  """',
        "",
        defs,
        "}",
    ]
    return "\n".join(lines) + "\n"


def specs2_nested(cls: str, mode: str, pkg: str = "example") -> str:
    """specs2 mutable Specification using nested `>>` blocks (vs the `should`/`in`
    form of the `mutable` style)."""
    lines = [
        f"package {pkg}",
        "",
        "import org.specs2.mutable.Specification",
        "",
        f"class {cls} extends Specification {{",
        '  "Calculator" >> {',
    ]
    for label, expr, exp in _st_cases(mode):
        lines += [f'    "{label}" >> {{', f"      {expr} must beEqualTo({exp})", "    }"]
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def defect_file(obj: str, variant: str) -> str:
    """One self-contained defect-bearing object. variant: warn | error.

    Used for agnostic compile-only situations, where `large` means many files/issues
    (the migration shape, PLAN #7) — not a test count.
    """
    lines = [
        "package example",
        "",
        f"object {obj} {{",
    ]
    if variant == "warn":
        lines += [
            "  // non-exhaustive match on a sealed type -> 'match may not be exhaustive'",
            "  // warning, emitted by default on both 2.13 and 3.",
            "  def label(o: Option[Int]): String = o match {",
            '    case Some(n) => "some " + n',
            "  }",
        ]
    else:
        lines += [
            "  // deliberate type error -> compilation fails",
            '  val broken: Int = "not an int"',
        ]
    lines.append("}")
    return "\n".join(lines) + "\n"


# ============================================================================
#  library registry: deps + testFrameworks + style emitters per lib
# ============================================================================
# A style emitter has signature (cls, mode, pkg) -> source string.
# `deps` are `libraryDependencies +=` lines; `frameworks` are `testFrameworks +=`
# lines (only zio-test needs one — scalatest/specs2/munit auto-register via the
# sbt testing SPI, which bloopInstall carries into the .bloop config).
LIBS = {
    "munit": {
        "deps": [f'libraryDependencies += "org.scalameta" %% "munit" % "{V.MUNIT_VERSION}" % Test'],
        "frameworks": [],
        "test_cls": "CalculatorSuite",
        "styles": {
            "funsuite": munit_suite,        # representative (first listed)
            "clue": munit_clue,
            "scalacheck": munit_scalacheck,
        },
        # per-style extra deps (don't perturb the other styles' build.sbt)
        "style_deps": {
            "scalacheck": {
                "deps": [f'libraryDependencies += "org.scalameta" %% "munit-scalacheck" % "{V.MUNIT_SCALACHECK_VERSION}" % Test'],
            },
        },
    },
    "scalatest": {
        "deps": [f'libraryDependencies += "org.scalatest" %% "scalatest" % "{V.SCALATEST_VERSION}" % Test'],
        "frameworks": [],
        "test_cls": "CalculatorSuite",
        "styles": {
            "funsuite": scalatest_funsuite,     # representative (first listed)
            "flatspec": scalatest_flatspec,
            "funspec": scalatest_funspec,
            "wordspec": scalatest_wordspec,
            "freespec": scalatest_freespec,
            "propspec": scalatest_propspec,
            "featurespec": scalatest_featurespec,
            "refspec": scalatest_refspec,
            "matchers": scalatest_matchers,
        },
    },
    "specs2": {
        "deps": [f'libraryDependencies += "org.specs2" %% "specs2-core" % "{V.SPECS2_VERSION_3}" % Test'],
        "frameworks": [],
        "test_cls": "CalculatorSpec",
        "styles": {
            "mutable": specs2_mutable,       # representative (first listed)
            "acceptance": specs2_acceptance,
            "nested": specs2_nested,
        },
    },
    "ziotest": {  # token has no hyphen so it stays one fixture-name segment
        "deps": [
            f'libraryDependencies += "dev.zio" %% "zio-test" % "{V.ZIOTEST_VERSION}" % Test',
            f'libraryDependencies += "dev.zio" %% "zio-test-sbt" % "{V.ZIOTEST_VERSION}" % Test',
        ],
        "frameworks": ['testFrameworks += new TestFramework("zio.test.sbt.ZTestFramework")'],
        "test_cls": "CalculatorSpec",
        "styles": {
            "asserttrue": ziotest_asserttrue,   # representative (first listed)
            "assertion": ziotest_assertion,
            "nested": ziotest_nested,
            "effectful": ziotest_effectful,
        },
    },
}

# lib for the test-framework dependency: explicit lib, else munit (e.g. no_tests).
def lib_key(lib: str) -> str:
    return lib if lib else "munit"


def test_settings(lib: str, style: str = "") -> list:
    L = LIBS[lib_key(lib)]
    out = list(L["deps"]) + list(L["frameworks"])
    sd = L.get("style_deps", {}).get(style)
    if sd:
        out += list(sd.get("deps", [])) + list(sd.get("frameworks", []))
    return out


# ============================================================================
#  build files
# ============================================================================
def build_single(name: str, settings: list) -> str:
    block = "".join(f"\n    {s}," for s in settings)
    return (
        f'ThisBuild / scalaVersion := "{V.SCALA3_VERSION}"\n'
        "\n"
        "// parallelExecution off for deterministic ordering (PLAN #6); crossScalaVersions\n"
        "// declared for the Phase-3 dedup pass (capture stays Scala 3 through Phase 1).\n"
        'lazy val root = (project in file("."))\n'
        "  .settings(\n"
        f'    name := "{name}",\n'
        f'    crossScalaVersions := Seq("{V.SCALA213_VERSION}", "{V.SCALA3_VERSION}"),\n'
        "    Test / parallelExecution := false,"
        f"{block}\n"
        "  )\n"
    )


def build_mm(name: str, settings: list) -> str:
    inline = "".join(f", {s}" for s in settings)
    out = [
        f'ThisBuild / scalaVersion := "{V.SCALA3_VERSION}"',
        f'ThisBuild / crossScalaVersions := Seq("{V.SCALA213_VERSION}", "{V.SCALA3_VERSION}")',
        "ThisBuild / Test / parallelExecution := false",
        "",
    ]
    for m in MODULES:
        out += [
            f'lazy val {m} = (project in file("{m}"))',
            f'  .settings(name := "{m}"{inline})',
            "",
        ]
    out += [
        'lazy val root = (project in file("."))',
        f"  .aggregate({','.join(MODULES)})",
        f'  .settings(name := "{name}")',
    ]
    return "\n".join(out) + "\n"


def project_files(repo: Path) -> None:
    (repo / "project").mkdir(parents=True, exist_ok=True)
    write(repo / "project" / "build.properties", f"sbt.version={V.SBT_VERSION}\n")
    write(repo / "project" / "plugins.sbt",
          f'addSbtPlugin("ch.epfl.scala" % "sbt-bloop" % "{V.SBT_BLOOP_VERSION}")\n')
    write(repo / ".gitignore", "target/\n.bloop/\n.bsp/\n")


# ============================================================================
#  helpers
# ============================================================================
def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def suite_mode(situation: str) -> str:
    return {"pass": "pass", "fail": "fail", "warn_fail": "fail",
            "error": "error", "skipped": "skipped"}.get(situation, "pass")


def main_variant(situation: str) -> str:
    if situation in ("warn", "warn_fail"):
        return "warn"
    if situation == "compile_error":
        return "error"
    return "clean"


def emit_tests(testdir: Path, lib: str, style: str, mode: str, suites: int,
               pkg: str = "example") -> None:
    """Write the test suites for a module, using the lib's style emitter.

    `large` scales the suite *count* (CalculatorSuite1..N), keeping each suite the
    canonical small shape (repetition is the migration shape, PLAN #7).
    """
    L = LIBS[lib_key(lib)]
    emitter = L["styles"].get(style)
    if emitter is None:
        die(f"lib '{lib_key(lib)}' has no style '{style}' "
            f"(have: {', '.join(sorted(L['styles']))})")
    base = L["test_cls"]
    if suites > 1:
        for i in range(1, suites + 1):
            write(testdir / f"{base}{i}.scala", emitter(f"{base}{i}", mode, pkg))
    else:
        write(testdir / f"{base}.scala", emitter(base, mode, pkg))


# ============================================================================
#  drive
# ============================================================================
def main() -> None:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--lib", default="")
    p.add_argument("--style", default="")
    p.add_argument("--situation", required=True)
    p.add_argument("--scale", default="")
    p.add_argument("--topology", default="single")
    args = p.parse_args()

    lib, style, situation = args.lib, args.style, args.situation
    scale, topology = args.scale, args.topology

    agnostic = situation in AGNOSTIC_SITUATIONS
    if not agnostic:
        if not lib:
            die(f"situation '{situation}' requires --lib")
        if lib not in LIBS:
            die(f"unknown lib '{lib}' (have: {', '.join(sorted(LIBS))})")
        if not style:
            style = next(iter(LIBS[lib]["styles"]))   # representative = first listed

    if situation in TEST_COMMAND_SITUATIONS:
        command = "test"
    elif situation in COMPILE_COMMAND_SITUATIONS:
        command = "compile"
    else:
        die(f"unknown situation: {situation}")

    if situation in SCALELESS_SITUATIONS:
        scale = ""
    elif not scale:
        die(f"situation '{situation}' requires --scale small|large")

    sit_dash = situation.replace("_", "-")
    if topology == "mm":
        name = f"mm-{lib}-{sit_dash}" + (f"-{scale}" if scale else "")
    elif agnostic:
        name = f"_{sit_dash}" + (f"-{scale}" if scale else "")
    else:
        name = f"{lib}-{style}-{sit_dash}-{scale}"
    repo = ROOT / "repos" / name

    suites = 6 if scale == "large" else 1   # fixed canonical counts (PLAN #7)
    projects = " ".join(MODULES) if topology == "mm" else "root"
    needs_test_lib = situation in TEST_COMMAND_SITUATIONS

    # ---- regenerate sources (leave target/ .bloop/ .bsp/ untouched) ----------
    if (repo / "src").exists():
        shutil.rmtree(repo / "src")
    for m in MODULES:
        if (repo / m / "src").exists():
            shutil.rmtree(repo / m / "src")
    repo.mkdir(parents=True, exist_ok=True)
    project_files(repo)

    if topology == "mm":
        write(repo / "build.sbt", build_mm(name, test_settings(lib, style)))
        mode, mv = suite_mode(situation), main_variant(situation)
        for m in MODULES:
            write(repo / m / "src/main/scala/example/Calculator.scala", main_file(mv, f"example.{m}"))
            emit_tests(repo / m / "src/test/scala/example", lib, style, mode, suites, f"example.{m}")
    else:
        write(repo / "build.sbt", build_single(name, test_settings(lib, style) if needs_test_lib else []))
        if situation == "warn":
            for i in range(1, suites + 1):
                write(repo / f"src/main/scala/example/Defect{i}.scala", defect_file(f"Defect{i}", "warn"))
        elif situation == "compile_error":
            for i in range(1, suites + 1):
                write(repo / f"src/main/scala/example/Defect{i}.scala", defect_file(f"Defect{i}", "error"))
        else:
            write(repo / "src/main/scala/example/Calculator.scala", main_file(main_variant(situation)))
            if needs_test_lib and situation != "no_tests":
                emit_tests(repo / "src/test/scala/example", lib, style, suite_mode(situation), suites)

    # ---- meta ----------------------------------------------------------------
    write(repo / ".rsx-meta",
          "# generated by the generator — consumed by scripts/capture.sh (do not hand-edit)\n"
          f'LIB="{lib}"\n'
          f'STYLE="{style}"\n'
          f'SITUATION="{situation}"\n'
          f'SCALE="{scale}"\n'
          f'TOPOLOGY="{topology}"\n'
          f'AGNOSTIC="{1 if agnostic else 0}"\n'
          f'COMMAND="{command}"\n'
          f'PROJECTS="{projects}"\n')

    dash = "—"
    print(f"gen: wrote {repo} (lib={lib or dash} style={style or dash} "
          f"situation={situation} scale={scale or dash} topology={topology} "
          f"cmd={command} projects={projects})")


if __name__ == "__main__":
    main()
