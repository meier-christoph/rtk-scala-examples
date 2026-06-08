package example

import org.scalatest.propspec.AnyPropSpec
import org.scalatest.prop.TableDrivenPropertyChecks._

class CalculatorSuite extends AnyPropSpec {
  property("Calculator.add matches the table") {
    val cases = Table(
      ("a", "b", "sum"),
      (2, 3, 5),
      (10, 7, 99),
      (6, 7, 13),
      (20, 4, 24)
    )
    forAll(cases) { (a: Int, b: Int, sum: Int) =>
      assert(Calculator.add(a, b) == sum)
    }
  }
}
