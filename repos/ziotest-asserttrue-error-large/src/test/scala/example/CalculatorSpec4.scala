package example

import zio.test._

object CalculatorSpec4 extends ZIOSpecDefault {
  def spec = suite("Calculator")(
    test("add returns the sum") {
      val result = Calculator.add(2, 3)
      assertTrue(result == 5)
    },
    test("sub returns the difference") {
      val result = Calculator.sub(10, 4)
      assertTrue(result == 6)
    },
    test("mul returns the product") {
      val result = Calculator.mul(6, 7)
      assertTrue(result == 42)
    },
    test("div returns the quotient") {
      val result = Calculator.div(20, 0)
      assertTrue(result == 5)
    }
  ) @@ TestAspect.sequential
}
