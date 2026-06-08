package example

import zio.test._

object CalculatorSpec extends ZIOSpecDefault {
  def spec = suite("Calculator")(
    test("add returns the sum") {
      assert(Calculator.add(2, 3))(Assertion.equalTo(5))
    },
    test("sub returns the difference") {
      assert(Calculator.sub(10, 4))(Assertion.equalTo(7))
    },
    test("mul returns the product") {
      assert(Calculator.mul(6, 7))(Assertion.equalTo(42))
    },
    test("div returns the quotient") {
      assert(Calculator.div(20, 4))(Assertion.equalTo(4))
    }
  ) @@ TestAspect.sequential
}
