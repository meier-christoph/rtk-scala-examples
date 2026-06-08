package example

object Defect3 {
  // deliberate type error -> compilation fails
  val broken: Int = "not an int"
}
