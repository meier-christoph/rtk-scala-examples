package example

import org.scalacheck.Prop.forAll

class CalculatorSuite extends munit.ScalaCheckSuite {

  override def scalaCheckInitialSeed =
    "TO7zgUWdv-WPJuetViT8r85tY3TprSjGhdyoESCTTkI="

  property("add is commutative") {
    forAll { (a: Int, b: Int) =>
      Calculator.add(a, b) == Calculator.add(b, a)
    }
  }

  property("add zero is identity") {
    forAll { (n: Int) =>
      Calculator.add(n, 0) == (n + 1)
    }
  }
}
