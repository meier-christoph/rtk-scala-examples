package example

/** Structural dummy: reproduces output shape, not real domain logic. */
object Calculator {
  def add(a: Int, b: Int): Int = a + b
  def sub(a: Int, b: Int): Int = a - b
  def mul(a: Int, b: Int): Int = a * b
  def div(a: Int, b: Int): Int = a / b

  // non-exhaustive match on a sealed type (Option) -> 'match may not be
  // exhaustive' warning, emitted by default on both 2.13 and 3 (no flags).
  def label(o: Option[Int]): String = o match {
    case Some(n) => "some " + n
  }
}
