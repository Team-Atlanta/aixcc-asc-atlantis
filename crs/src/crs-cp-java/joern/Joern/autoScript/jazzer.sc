import io.shiftleft.codepropertygraph.Cpg
import io.shiftleft.semanticcpg.language._
import scala.jdk.CollectionConverters._
import java.nio.file.{Files, Paths, Path, StandardOpenOption}
import scala.sys.process._
import java.nio.charset.StandardCharsets

case class MethodCallInfo(callingMethod: String, calledMethod: String, calledMethodPackage: String)
case class MethodDefinitionInfo(methodFullName: String, filePath: String, startLine: Int, endLine: Int)

// Query to list all external functions being called within `fuzzerTestOneInput` and the functions it calls
def externalCalledFunctionsFromAllMethods(cpg: Cpg): List[MethodCallInfo] = {
  def getBasePackage(methodFullName: String): String = {
    methodFullName.split('.').dropRight(2).mkString(".")
  }

  def cleanPackageName(packageName: String): String = {
    packageName.replaceAll("\\$.*$", "")
  }

  def getCalledMethods(methodFullName: String): List[MethodCallInfo] = {
    cpg.method.fullNameExact(methodFullName).call.filter { call =>
      !call.methodFullName.contains("<init>") && !call.methodFullName.contains("<clinit>")
    }.map { call =>
      val calledMethod = call.methodFullName
      val calledMethodPackage = cleanPackageName(calledMethod.split(':').dropRight(1).mkString("").split('.').dropRight(1).mkString("."))
      MethodCallInfo(methodFullName, calledMethod, calledMethodPackage)
    }.toList.distinct
  }

  // Recursively get all methods called, including external calls
  def getAllExternalCalls(methodNames: List[String], basePackage: String, seen: Set[String] = Set.empty): List[MethodCallInfo] = {
    methodNames.flatMap { methodName =>
      if (!seen.contains(methodName)) {
        val directCalls = getCalledMethods(methodName)
        val externalCalls = directCalls.filter { callInfo =>
          callInfo.calledMethodPackage.nonEmpty
        }
        externalCalls ++ getAllExternalCalls(directCalls.map(_.calledMethod), basePackage, seen + methodName)
      } else {
        List.empty
      }
    }.distinct
  }

  // Retrieve all methods to start the analysis
  val allMethods = cpg.method.fullName.l
  val allExternalCalls = allMethods.flatMap { methodFullName =>
    val basePackage = getBasePackage(methodFullName)
    val initialCalls = getCalledMethods(methodFullName)
    getAllExternalCalls(initialCalls.map(_.calledMethod), basePackage)
  }

  allExternalCalls.distinct
}

// Function to find method definitions in provided paths
def findMethodDefinitions(cpg: Cpg, methods: List[MethodCallInfo], paths: String): List[MethodDefinitionInfo] = {
  val pathList = paths.split(":").toList
  val testPatterns = List("test", "Test", "spec", "Spec", "mock", "Mock")

  methods.flatMap { methodInfo =>
    val methodName = methodInfo.calledMethod.split(':').head.split('.').last
    val escapedMethodName = java.util.regex.Pattern.quote(methodName)
    val packagePath = methodInfo.calledMethodPackage.replace('.', '/')
    pathList.flatMap { path =>
      val filePath = Paths.get(path)
      if (Files.exists(filePath) && Files.isDirectory(filePath)) {
        val javaFiles = Files.walk(filePath).iterator().asScala.filter(_.toString.endsWith(".java")).toList
        javaFiles.flatMap { file =>
          if (testPatterns.exists(pattern => file.toString.contains(pattern)) || !file.toString.contains(packagePath)) {
            List.empty
          } else {
            val content = Files.readAllLines(file).asScala.mkString("\n")
            val regex = s"\\b$escapedMethodName\\b".r
            regex.findAllMatchIn(content).map { m =>
              val startLine = content.substring(0, m.start).split("\n").length
              val endLine = startLine + content.substring(m.start).split("\n").takeWhile(!_.contains("}")).length - 1
              MethodDefinitionInfo(methodInfo.calledMethod, file.toString, startLine, endLine)
            }.toList
          }
        }
      } else {
        List.empty
      }
    }
  }.distinct
}

// Function to find the repository path for a given file
def findRepositoryPath(filePath: String, repoPaths: List[String]): Option[String] = {
  repoPaths.find { repoPath =>
    val resolvedPath = Paths.get(repoPath).resolve(Paths.get(filePath))
    val relativePath = Paths.get(repoPath).relativize(Paths.get(filePath)).toString
    Files.exists(resolvedPath) && !relativePath.contains("..")
  }
}

// Function to check if a file has been modified after the first commit
def hasFileBeenModifiedAfterFirstCommit(filePath: String, repoPath: String): Boolean = {
  println(s"Checking if file $filePath in repo $repoPath has been modified after the first commit.")
  try {
    val relativePath = Paths.get(repoPath).relativize(Paths.get(filePath)).toString
    val firstCommitHash = Seq("git", "-C", repoPath, "rev-list", "--max-parents=0", "HEAD").!!.trim
    val logOutput = Seq("git", "-C", repoPath, "log", "--pretty=format:%H", "--follow", relativePath).!!.trim
    val commits = logOutput.split("\n")
    val hasBeenModified = commits.exists(_ != firstCommitHash)
    println(s"File $filePath has been modified: $hasBeenModified")
    hasBeenModified
  } catch {
    case e: Exception =>
      println(s"Error checking file $filePath in repo $repoPath: ${e.getMessage}")
      false
  }
}

// Filter method definitions based on Git history
def filterMethodDefinitionsByGitHistory(methodDefinitions: List[MethodDefinitionInfo], repoPaths: List[String]): List[MethodDefinitionInfo] = {
  val modified = methodDefinitions.filter { methodDef =>
    findRepositoryPath(methodDef.filePath, repoPaths).exists { repoPath =>
      println(s"Found repo path for ${methodDef.filePath}: $repoPath")
      hasFileBeenModifiedAfterFirstCommit(methodDef.filePath, repoPath)
    }
  }

  val unmodified = methodDefinitions.filterNot { methodDef =>
    modified.contains(methodDef)
  }

  (modified ++ unmodified).distinct
}

// Save results to an output file
def saveResultsToFile(results: List[MethodDefinitionInfo], outputPath: String): Unit = {
  val outputData = results.map { case MethodDefinitionInfo(fullName, fileName, startLine, endLine) =>
    s"$fullName :: $fileName :: $startLine :: $endLine ::"
  }.mkString("\n")

  Files.write(Paths.get(outputPath), outputData.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)
}

// Main function to run the script
def main(): Unit = {

  val gitRepoPaths = "<git_dir>"
  val outputFilePath = "<output>"

  // Execute the query to find external method calls
  val externalMethods = externalCalledFunctionsFromAllMethods(cpg)

  // Find method definitions in the provided paths, ignoring test classes
  val methodDefinitions = findMethodDefinitions(cpg, externalMethods, gitRepoPaths)
  println(s"Found method definitions: ${methodDefinitions.size}")

  // Filter method definitions based on Git history
  val repoPaths = gitRepoPaths.split(":").toList
  val filteredDefinitions = filterMethodDefinitionsByGitHistory(methodDefinitions, repoPaths)

  // Ensure uniqueness based on methodFullName
  val uniqueDefinitions = filteredDefinitions.groupBy(_.methodFullName).map(_._2.head).toList
  println(s"All relevant method definitions: ${uniqueDefinitions.size}")

  // Print the method definitions
  uniqueDefinitions.foreach { case MethodDefinitionInfo(methodFullName, filePath, startLine, endLine) =>
    println(s"Method: $methodFullName, File: $filePath, Start Line: $startLine, End Line: $endLine")
  }

  // Save the filtered method definitions to the output file
  saveResultsToFile(uniqueDefinitions, outputFilePath)
  println(s"Results saved to $outputFilePath")
}

// Run the main function with arguments
main()
