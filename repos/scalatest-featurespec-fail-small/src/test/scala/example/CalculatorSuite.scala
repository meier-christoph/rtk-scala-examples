package example

import org.scalatest.featurespec.AnyFeatureSpec
import org.scalatest.GivenWhenThen

class CalculatorSuite extends AnyFeatureSpec with GivenWhenThen {
  Feature("Calculator arithmetic") {
    Scenario("add returns the sum") {
      Given("two operands")
      When("the operation runs")
      Then("the result is 5")
      assert(Calculator.add(2, 3) == 5)
    }
    Scenario("sub returns the difference") {
      Given("two operands")
      When("the operation runs")
      Then("the result is 7")
      assert(Calculator.sub(10, 4) == 7)
    }
    Scenario("mul returns the product") {
      Given("two operands")
      When("the operation runs")
      Then("the result is 42")
      assert(Calculator.mul(6, 7) == 42)
    }
    Scenario("div returns the quotient") {
      Given("two operands")
      When("the operation runs")
      Then("the result is 4")
      assert(Calculator.div(20, 4) == 4)
    }
  }
}
