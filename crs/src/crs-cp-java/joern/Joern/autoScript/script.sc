import scala.collection.mutable
 val methodCallCounts = mutable.Map[String, String]()
val testMethods = cpg.method.fullName.l
testMethods.foreach { methodName =>
  // Print the test method and its containing file for context
  val methodNode = cpg.method.fullNameExact(methodName).head
  
  //println(s"Test method: $methodName in file: ${methodNode.file.name.l.head}")
  // Find calls within the test method that are not related to testing frameworks
  methodNode.call
    .name.l
    .filterNot(name =>
      name.startsWith("assert") ||
      name.startsWith("mock") ||
      name.startsWith("verify") ||
      name.startsWith("setUp") ||
      name.startsWith("tearDown") ||
      name.startsWith("when")) 
    .foreach { calledMethodName =>
      val calledMethod = cpg.method.nameExact(calledMethodName).headOption
      calledMethod match {
        case Some(m) =>
          if(m.fullName.contains("jenkins") && !m.fullName.split('.').dropRight(1).mkString(".").contains(m.name) && !methodName.contains(m.fullName.split('.').dropRight(1).mkString(".") )){
println(s"Test method: $methodName in file: ${methodNode.file.name.l.head}")  
methodCallCounts(m.name.toString())=m.fullName.split('.').dropRight(1).mkString(".")        
println(s" - calls application method: ${m.name} from package: ${m.fullName.split('.').dropRight(1).mkString(".")}")
           }
        case None =>
          println(s" - calls external or unknown method: $calledMethodName")
      }
    }
}
methodCallCounts
