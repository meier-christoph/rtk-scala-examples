package example

import org.specs2.mutable.Specification

class CalculatorSpec extends Specification {
  "Calculator" >> {
    "add returns the sum" >> {
      Calculator.add(2, 3) must beEqualTo(5)
    }
    "sub returns the difference" >> {
      Calculator.sub(10, 4) must beEqualTo(7)
    }
    "mul returns the product" >> {
      Calculator.mul(6, 7) must beEqualTo(42)
    }
    "div returns the quotient" >> {
      Calculator.div(20, 4) must beEqualTo(4)
    }
  }
}
