package example

import org.scalatest.freespec.AnyFreeSpec

class CalculatorSuite extends AnyFreeSpec {
  "Calculator" - {
    "add returns the sum" in {
      assert(Calculator.add(2, 3) == 5)
    }
    "sub returns the difference" in {
      assert(Calculator.sub(10, 4) == 7)
    }
    "mul returns the product" in {
      assert(Calculator.mul(6, 7) == 42)
    }
    "div returns the quotient" in {
      assert(Calculator.div(20, 4) == 4)
    }
  }
}
