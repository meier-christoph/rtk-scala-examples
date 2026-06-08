package example

import org.scalatest.funsuite.AnyFunSuite

class CalculatorSuite2 extends AnyFunSuite {

  test("add returns the sum") {
    assert(Calculator.add(2, 3) == 5)
  }

  test("sub returns the difference") {
    assert(Calculator.sub(10, 4) == 6)
  }

  test("mul returns the product") {
    assert(Calculator.mul(6, 7) == 42)
  }

  test("div returns the quotient") {
    assert(Calculator.div(20, 4) == 5)
  }
}
