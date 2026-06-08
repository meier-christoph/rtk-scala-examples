package example

import zio._
import zio.test._

object CalculatorSpec extends ZIOSpecDefault {
  def spec = suite("Calculator")(
    test("add returns the sum") {
      for {
        result <- ZIO.succeed(Calculator.add(2, 3))
      } yield assertTrue(result == 5)
    },
    test("sub returns the difference") {
      for {
        result <- ZIO.succeed(Calculator.sub(10, 4))
      } yield assertTrue(result == 7)
    },
    test("mul returns the product") {
      for {
        result <- ZIO.succeed(Calculator.mul(6, 7))
      } yield assertTrue(result == 42)
    },
    test("div returns the quotient") {
      for {
        result <- ZIO.succeed(Calculator.div(20, 4))
      } yield assertTrue(result == 4)
    }
  ) @@ TestAspect.sequential
}
