package example

object Defect4 {
  // deliberate type error -> compilation fails
  val broken: Int = "not an int"
}
