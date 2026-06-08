package example

class CalculatorSuite3 extends munit.FunSuite {

  test("add returns the sum") {
    assertEquals(Calculator.add(2, 3), 5)
  }

  test("sub returns the difference") {
    assertEquals(Calculator.sub(10, 4), 6)
  }

  test("mul returns the product") {
    assertEquals(Calculator.mul(6, 7), 42)
  }

  test("div returns the quotient") {
    assertEquals(Calculator.div(20, 4), 5)
  }
}
