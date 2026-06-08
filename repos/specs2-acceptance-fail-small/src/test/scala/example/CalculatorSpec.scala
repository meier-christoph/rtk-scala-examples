package example

import org.specs2.Specification

class CalculatorSpec extends Specification { def is = s2"""
  Calculator should
    add returns the sum $add
    sub returns the difference $sub
    mul returns the product $mul
    div returns the quotient $div
  """

  def add = Calculator.add(2, 3) must beEqualTo(5)
  def sub = Calculator.sub(10, 4) must beEqualTo(7)
  def mul = Calculator.mul(6, 7) must beEqualTo(42)
  def div = Calculator.div(20, 4) must beEqualTo(4)
}
