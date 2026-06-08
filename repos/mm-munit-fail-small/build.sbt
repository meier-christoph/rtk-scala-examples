ThisBuild / scalaVersion := "3.3.7"
ThisBuild / crossScalaVersions := Seq("2.13.16", "3.3.7")
ThisBuild / Test / parallelExecution := false

lazy val core = (project in file("core"))
  .settings(name := "core", libraryDependencies += "org.scalameta" %% "munit" % "1.3.2" % Test)

lazy val util = (project in file("util"))
  .settings(name := "util", libraryDependencies += "org.scalameta" %% "munit" % "1.3.2" % Test)

lazy val root = (project in file("."))
  .aggregate(core,util)
  .settings(name := "mm-munit-fail-small")
