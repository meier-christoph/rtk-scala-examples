package example

object Defect2 {
  // deliberate type error -> compilation fails
  val broken: Int = "not an int"
}
