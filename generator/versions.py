"""Central version pins for rtk-scala-examples.

Single source of truth for the generator. (The capture scripts don't consume these —
they pin JDK/tooling in scripts/lib.sh — so pins live here in Python only.)
"""

SBT_VERSION = "1.12.11"
SCALA3_VERSION = "3.3.7"        # latest 3.3 LTS
SCALA213_VERSION = "2.13.16"
SBT_BLOOP_VERSION = "2.1.0"

# Test libraries (all verified in the PKI mirror for Scala 3 on 2026-06-05)
MUNIT_VERSION = "1.3.2"
MUNIT_SCALACHECK_VERSION = "1.3.0"
SCALATEST_VERSION = "3.2.19"
SPECS2_VERSION_213 = "4.20.9"
SPECS2_VERSION_3 = "5.9.0"
ZIOTEST_VERSION = "2.1.26"

# Default Scala version for single-version generation / Phase 0–1
DEFAULT_SCALA_VERSION = SCALA3_VERSION
