import io.shiftleft.semanticcpg.language._
import io.shiftleft.semanticcpg.language.operatorextension._


val entryPoint = cpg.method.name("fuzzerTestOneInput").headOption.getOrElse(null)

if (entryPoint != null) {
  println("Entry Point: " + entryPoint.fullName)

 
  val dataVar = entryPoint.parameter.name("data").headOption.getOrElse(null)
  if (dataVar != null) {
    val dataUsage = entryPoint.block.ast.isCall.filter(call => call.code.contains("data")).l
    println("Data Usage: ")
    dataUsage.foreach(call => println(s" - ${call.code}"))

    
    val fileInputUsage = entryPoint.block.ast.isCall.filter(call => call.code.contains("filename") || call.code.contains("FileInputStream")).l
    if (fileInputUsage.nonEmpty) {
      println("\nFile Input Usage: ")
      fileInputUsage.foreach(call => println(s" - ${call.code}"))
    }

   
    val partsUsage = entryPoint.block.ast.isCall.filter(call => call.code.contains("parts")).l
    println("\nParts Usage: ")
    partsUsage.foreach(call => println(s" - ${call.code}"))

    
    val dataOperations = (dataUsage ++ fileInputUsage ++ partsUsage).flatMap { call =>
      call.argument.isCall.map(argCall => (argCall.code, call.code))
    }.distinct
    println("\nData Operations: ")
    dataOperations.foreach { case (operation, originalCall) =>
      println(s" - Operation: $operation, Original Call: $originalCall")
    }

    
    val encodingMethods = entryPoint.block.ast.isCall.filter { call =>
      call.methodFullName.contains("base64") || call.methodFullName.contains("encode") || call.methodFullName.contains("encrypt")
    }.l
    if (encodingMethods.nonEmpty) {
      println("\nEncoding Methods: ")
      encodingMethods.foreach { method =>
        println(s" - ${method.methodFullName}")
      }
    }

  
    val inputNature = entryPoint.block.ast.isCall.filter(call => call.methodFullName.contains("split") || call.methodFullName.contains("String")).l
    println("\nInput Nature: ")
    inputNature.foreach { call =>
      println(s" - ${call.code}")
    }

    // Analyze headers and commands related to Jenkins
    val headers = entryPoint.block.ast.isCall.filter(call => call.methodFullName.contains("getParameter")).l
    println("\nHeaders: ")
    headers.foreach { call =>
      println(s" - ${call.code}")
    }

    // Identify commands related to Jenkins
    val jenkinsCommands = entryPoint.block.ast.isCall.filter(call => 
      call.methodFullName.contains("jenkins.model.Jenkins") ||
      call.methodFullName.contains("hudson.model") ||
      call.methodFullName.contains("org.kohsuke.stapler")
    ).l
    println("\nJenkins Commands: ")
    jenkinsCommands.foreach { call =>
      println(s" - ${call.code}")

      // Identify conditions to reach the command function (Jenkins related)
      val conditions = call.inAstMinusLeaf.isControlStructure.condition.l
      val relevantConditions = conditions.filterNot(cond => cond.code.contains("System.exit") || cond.code.contains("Exception"))
      println("\nConditions to Reach Command (excluding exceptions or System.exit): ")
      relevantConditions.foreach { condition =>
        println(s" - Condition: ${condition.code}")

        // Determine if the condition or its negation leads to the command
        val controlStructure = condition.inAstMinusLeaf.isControlStructure.headOption
        controlStructure match {
          case Some(ctrlStruct) =>
            val positivePath = ctrlStruct.whenTrue.ast.isCall.l
            val negativePath = ctrlStruct.whenFalse.ast.isCall.l

            if (positivePath.exists(_.id == call.id)) {
              println(s"   -> The condition leads to the command: ${condition.code}")
            }
            if (negativePath.exists(_.id == call.id)) {
              println(s"   -> The negation of the condition leads to the command: !(${condition.code})")
            }
          case None => println("   -> No control structure found for the condition.")
        }
      }

      // 7. Extract and display all string literals in the method
      val stringLiterals = entryPoint.ast.isLiteral.code(".*\".*\".*").l
     

      // 8. Suggest potential input values based on conditions and string literals
      println("\nPotential Input Values to Reach Command: ")
      relevantConditions.foreach { condition =>
        val conditionCode = condition.code
        println(s" - Condition: $conditionCode")
        val potentialValues = stringLiterals.filter(literal => conditionCode.contains(literal.code.stripPrefix("\"").stripSuffix("\"")))
        potentialValues.foreach { value =>
          println(s"   -> Potential Value: ${value.code}")
        }
      }
    }
  } else {
    println("Data parameter 'data' not found in entry point method")
  }
} else {
  println("Entry point method 'fuzzerTestOneInput' not found")
}

