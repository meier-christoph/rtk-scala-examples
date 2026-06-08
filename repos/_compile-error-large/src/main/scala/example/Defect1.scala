package example

object Defect1 {
  // deliberate type error -> compilation fails
  val broken: Int = "not an int"
}
