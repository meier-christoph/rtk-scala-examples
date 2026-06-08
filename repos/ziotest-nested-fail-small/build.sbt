ThisBuild / scalaVersion := "3.3.7"

// parallelExecution off for deterministic ordering (PLAN #6); crossScalaVersions
// declared for the Phase-3 dedup pass (capture stays Scala 3 through Phase 1).
lazy val root = (project in file("."))
  .settings(
    name := "ziotest-nested-fail-small",
    crossScalaVersions := Seq("2.13.16", "3.3.7"),
    Test / parallelExecution := false,
    libraryDependencies += "dev.zio" %% "zio-test" % "2.1.26" % Test,
    libraryDependencies += "dev.zio" %% "zio-test-sbt" % "2.1.26" % Test,
    testFrameworks += new TestFramework("zio.test.sbt.ZTestFramework"),
  )
