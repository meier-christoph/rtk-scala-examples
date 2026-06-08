package example

import org.scalatest.funspec.AnyFunSpec

class CalculatorSuite extends AnyFunSpec {
  describe("Calculator") {
    it("add returns the sum") {
      assert(Calculator.add(2, 3) == 5)
    }
    it("sub returns the difference") {
      assert(Calculator.sub(10, 4) == 7)
    }
    it("mul returns the product") {
      assert(Calculator.mul(6, 7) == 42)
    }
    it("div returns the quotient") {
      assert(Calculator.div(20, 4) == 4)
    }
  }
}
