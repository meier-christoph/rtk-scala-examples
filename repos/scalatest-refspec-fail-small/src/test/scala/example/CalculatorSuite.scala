package example

import org.scalatest.refspec.RefSpec

class CalculatorSuite extends RefSpec {
  def `add returns the sum`(): Unit = assert(Calculator.add(2, 3) == 5)
  def `sub returns the difference`(): Unit = assert(Calculator.sub(10, 4) == 7)
  def `mul returns the product`(): Unit = assert(Calculator.mul(6, 7) == 42)
  def `div returns the quotient`(): Unit = assert(Calculator.div(20, 4) == 4)
}
