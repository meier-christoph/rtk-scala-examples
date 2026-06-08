package example

class CalculatorSuite extends munit.FunSuite {

  test("add returns the sum") {
    assert(clue(Calculator.add(2, 3)) == clue(5))
  }

  test("sub returns the difference") {
    assert(clue(Calculator.sub(10, 4)) == clue(7))
  }

  test("mul returns the product") {
    assert(clue(Calculator.mul(6, 7)) == clue(42))
  }

  test("div returns the quotient") {
    assert(clue(Calculator.div(20, 4)) == clue(4))
  }
}
