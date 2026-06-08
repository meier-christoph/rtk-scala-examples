ThisBuild / scalaVersion := "3.3.7"

// parallelExecution off for deterministic ordering (PLAN #6); crossScalaVersions
// declared for the Phase-3 dedup pass (capture stays Scala 3 through Phase 1).
lazy val root = (project in file("."))
  .settings(
    name := "_compile-pass",
    crossScalaVersions := Seq("2.13.16", "3.3.7"),
    Test / parallelExecution := false,
  )
