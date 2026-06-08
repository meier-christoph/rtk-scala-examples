package example

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class CalculatorSuite extends AnyFunSuite with Matchers {

  test("add returns the sum") {
    Calculator.add(2, 3) shouldBe 5
  }

  test("sub returns the difference") {
    Calculator.sub(10, 4) shouldBe 7
  }

  test("mul returns the product") {
    Calculator.mul(6, 7) shouldBe 42
  }

  test("div returns the quotient") {
    Calculator.div(20, 4) shouldBe 4
  }
}
