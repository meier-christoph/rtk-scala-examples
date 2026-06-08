package example

import org.specs2.mutable.Specification

class CalculatorSpec5 extends Specification {
  "Calculator" should {
    "add returns the sum" in {
      Calculator.add(2, 3) must beEqualTo(5)
    }
    "sub returns the difference" in {
      Calculator.sub(10, 4) must beEqualTo(6)
    }
    "mul returns the product" in {
      Calculator.mul(6, 7) must beEqualTo(42)
    }
    "div returns the quotient" in {
      Calculator.div(20, 4) must beEqualTo(5)
    }
  }
}
