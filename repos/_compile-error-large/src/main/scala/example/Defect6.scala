package example

object Defect6 {
  // deliberate type error -> compilation fails
  val broken: Int = "not an int"
}
