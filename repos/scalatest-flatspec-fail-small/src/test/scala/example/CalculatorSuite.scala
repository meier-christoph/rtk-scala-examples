package example

import org.scalatest.flatspec.AnyFlatSpec

class CalculatorSuite extends AnyFlatSpec {

  "Calculator" should "add returns the sum" in {
    assert(Calculator.add(2, 3) == 5)
  }

  it should "sub returns the difference" in {
    assert(Calculator.sub(10, 4) == 7)
  }

  it should "mul returns the product" in {
    assert(Calculator.mul(6, 7) == 42)
  }

  it should "div returns the quotient" in {
    assert(Calculator.div(20, 4) == 4)
  }
}
