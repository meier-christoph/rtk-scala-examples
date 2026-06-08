package example

object Defect4 {
  // non-exhaustive match on a sealed type -> 'match may not be exhaustive'
  // warning, emitted by default on both 2.13 and 3.
  def label(o: Option[Int]): String = o match {
    case Some(n) => "some " + n
  }
}
