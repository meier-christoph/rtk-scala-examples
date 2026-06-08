package example

object Defect5 {
  // deliberate type error -> compilation fails
  val broken: Int = "not an int"
}
