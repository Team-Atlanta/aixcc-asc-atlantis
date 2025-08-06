import io.shiftleft.codepropertygraph.generated.nodes.Call
import io.joern.dataflowengineoss.semanticsloader.{Parser, Semantics, FlowSemantic}
import io.joern.dataflowengineoss.DefaultSemantics
import java.nio.file.{Files, Paths, StandardOpenOption}
import java.nio.charset.StandardCharsets
import org.json4s._
import org.json4s.native.JsonMethods._
import org.json4s.native.Serialization
import org.json4s.native.Serialization.writePretty
import org.json4s.JsonDSL._
import scala.io.Source
import scala.util.{Try, Success, Failure}

object UserSemantic {
  def get_semantic_dir(): String = {
    Option(System.getenv("SEMANTIC_DIR")).getOrElse("")
  }

  def loadFlowSemantics(semanticPath: String): List[FlowSemantic] = {
    try {
      if (semanticPath.endsWith(".sem")) new Parser().parseFile(semanticPath) else List()
    } catch {
      case _ => List()
    }
  }

  def loadFlowSemanticsFromDir(semanticDir: String): List[FlowSemantic] = {
    try {
      val dirPath = Paths.get(semanticDir)
      val semPaths = Files.list(dirPath).iterator().asScala.toList
          .filterNot(path => Files.isDirectory(path))
          .filter(path => path.toString.endsWith(".sem"))
      semPaths.map(
        semanticPath => UserSemantic.loadFlowSemantics(semanticPath.toString)
      ).flatten
    } catch {
      case _ => List()
    }
  }

  def updateSemanticsFromDir(semanticDir: String): Unit = {
    DefaultSemantics.userSemantics ++= UserSemantic.loadFlowSemanticsFromDir(semanticDir)
  }
}

def get_basedir(): String = {
  Option(System.getenv("BASE_DIR")).getOrElse("")
}

class FileReader(val basedir: String, sentinel_node: Option[CfgNode]) {
  val sentinel: Option[(String, Int, Int)] = {
    sentinel_node match {
      case Some(x) =>
        for {
          filePath <- x.method.typeDecl.filename.headOption
          lineNumber <- x.lineNumber
          columnNumber <- x.columnNumber
        } yield (filePath, lineNumber, columnNumber)
      case _ => None
    }
  }

  def read(path: String, lineStart: Int, lineEnd: Int): String = {
    val lines = Source
      .fromFile(Paths.get(basedir, path).toFile)
      .getLines()
      .toList
      .slice(lineStart - 1, lineEnd)
    (sentinel match {
      case Some(x) if x._1 == path && x._2 >= lineStart && x._2 <= lineEnd =>
        lines.zipWithIndex.map { case (line, idx) =>
          if (idx + lineStart == x._2) {
            line.patch(x._3 - 1, "/*INJECTION*/", 0)
          } else {
            line
          }
        }
      case _ => lines
    }).mkString("\n")
  }
}

// TODO: Rename sentinel as more general one.
object Sentinel {
  def get(flow: Path): Option[CfgNode] = {
    flow.elements
      .filter(isSentinelType)
      .lastOption
      .map(node => Some(node.asInstanceOf[CfgNode]))
      .getOrElse(None)
  }

  private def isSentinelType(node: AstNode): Boolean = {
    if (node.columnNumber.getOrElse(-1) == -1)
      return false
    val typeFullName = node match {
      case x: Identifier => x.typeFullName
      case x: io.shiftleft.codepropertygraph.generated.nodes.Call =>
        x.typeFullName
      case _ => ""
    }
    // TODO: We may need more types.
    typeFullName == "java.lang.String"
  }
}

class CodeSnippetClass(val typeDecl: TypeDecl) {
  val staticFields = scala.collection.mutable.ListBuffer[CfgNode]()
  val staticBlocks = scala.collection.mutable.ListBuffer[Method]()
  val fields = scala.collection.mutable.ListBuffer[CfgNode]()
  val constructors = scala.collection.mutable.ListBuffer[Method]()
  val methods = scala.collection.mutable.ListBuffer[Method]()

  def addStaticField(node: CfgNode): Unit = {
    if (staticFields.contains(node)) return
    staticFields += node
  }

  def addStaticBlock(method: Method): Unit = {
    if (staticBlocks.contains(method)) return
    staticBlocks += method
  }

  def addField(node: CfgNode): Unit = {
    if (fields.contains(node)) return
    fields += node
  }

  def addConstructor(method: Method): Unit = {
    if (constructors.contains(method)) return
    constructors += method
  }

  def addMethod(method: Method): Unit = {
    if (methods.contains(method)) return
    methods += method
  }

  def build(basedir: String, sentinel: Option[CfgNode] = None): String = {
    def replaceFieldCode(code: String, instance: String): String = {
      val pattern = s"""\\b$instance\\.""".r
      pattern.replaceAllIn(code, "")
    }

    val sb = new StringBuilder
    val typeDeclFullName = typeDecl.fullName
    val (packageName, className) = typeDeclFullName.lastIndexOf(".") match {
      case x if x != -1 =>
        (
          Some(typeDeclFullName.substring(0, x)),
          typeDeclFullName.substring(x + 1)
        )
      case _ => (None, typeDeclFullName)
    }
    packageName match {
      case Some(x) => sb.append(s"package $x\n")
      case _       =>
    }
    sb.append(s"class $className {\n")

    staticFields
      .map(staticField => replaceFieldCode(staticField.code, typeDecl.name))
      .foreach(code => sb.append(s"static $code\n"))
    staticBlocks
      .filter(staticBlock => staticBlock.code != "<empty>")
      .foreach(staticBlock => sb.append(s"${staticBlock.code}\n"))
    fields
      .map(field => replaceFieldCode(field.code, "this"))
      .foreach(code => sb.append(s"$code\n"))
    val reader = FileReader(basedir, sentinel)
    constructors
      .flatMap(constructor => getCodeFromFile(reader, constructor))
      .foreach(code => sb.append(s"${code}\n"))
    methods
      .flatMap(method => getCodeFromFile(reader, method))
      .foreach(code => sb.append(s"${code}\n"))
    sb.append("}\n")
    sb.toString
  }

  private def getCodeFromFile(
      reader: FileReader,
      method: Method
  ): Option[String] = {
    for {
      methodFileName <- method.typeDecl.filename.headOption
      methodLineNumber <- method.lineNumber
      methodLineNumberEnd <- method.lineNumberEnd
    } yield {
      reader.read(methodFileName, methodLineNumber, methodLineNumberEnd)
    }
  }
}

def createCodeSnippet(flow: Path): List[CodeSnippetClass] = {
  val addedMethods = scala.collection.mutable.Set[Method]()
  val classes = scala.collection.mutable.Map[TypeDecl, CodeSnippetClass]()
  val buffer = scala.collection.mutable.ListBuffer[CodeSnippetClass]()

  def collectFields(methods: List[Method]): List[CfgNode] = {
    val scopes = methods.flatMap(method =>
      for {
        lineNumber <- method.lineNumber
        lineNumberEnd <- method.lineNumberEnd
      } yield (lineNumber, lineNumberEnd)
    )
    methods.flatMap(_.assignment.l).flatMap { node =>
      node.lineNumber match {
        case Some(x) =>
          val withinScope = scopes.exists { case (lineStart, lineEnd) =>
            x >= lineStart && x <= lineEnd
          }
          if (!withinScope) Some(node) else None
        case None => None
      }
    }
  }

  def getCallees(method: Method): List[Method] = {
    method.callee
      .whereNot(_.name("^<operator>.*"))
      .filterNot(_.isExternal)
      .l
      .distinct
  }

  def putToClassMap(method: Method): Unit = {
    if (addedMethods.contains(method)) {
      return
    }
    addedMethods.add(method)

    val typeDecl = method.typeDecl match {
      case Some(x) => x
      case None    => return
    }
    val codeSnippetClass =
      classes.getOrElseUpdate(typeDecl, CodeSnippetClass(typeDecl))
    val staticBlocks =
      method.typeDecl.method.where(_.name("^<clinit>|<clinitblock>$")).l
    val staticFields = collectFields(staticBlocks)

    staticFields.foreach(codeSnippetClass.addStaticField)
    staticBlocks.foreach(codeSnippetClass.addStaticBlock)
    staticBlocks.flatMap(getCallees).foreach(putToClassMap)
    if (method.name == "<clinitblock>") {
      return
    }

    if (method.isStatic.size > 0) {
      codeSnippetClass.addMethod(method)
      return
    }

    val constructors = method.typeDecl.method.where(_.nameExact("<init>")).l
    val fields = collectFields(constructors)

    fields.foreach(codeSnippetClass.addField)

    if (method.name == "<init>") {
      codeSnippetClass.addConstructor(method)
      return
    }

    if (codeSnippetClass.constructors.size == 0) {
      constructors.foreach(codeSnippetClass.addMethod)
      constructors.flatMap(getCallees).foreach(putToClassMap)
    }
    codeSnippetClass.addMethod(method)
  }

  flow.elements
    .map(_.asInstanceOf[CfgNode])
    .method
    .l
    .distinct
    .foreach(putToClassMap)
  flow.elements
    .map(_.asInstanceOf[CfgNode])
    .method
    .typeDecl
    .l
    .distinct
    .flatMap(typeDecl => classes.get(typeDecl))
}

case class Report(
    test_harness_path: String,
    sanitizer: String,
    code: String
)

def source(harness_paths: Set[String]) = {
  cpg.argument
    .where(_.method.nameExact("fuzzerTestOneInput"))
    .where(_.argumentIndexGt(0))
    .filter(arg => {
      arg.method.typeDecl.filename.toSet.intersect(harness_paths).size > 0
    })
}

def getCallees(
    m: Method,
    v: scala.collection.mutable.Set[Method]
): List[Method] = {
  val callees = m.callee
    .whereNot(_.name("^<operator>.*"))
    .filterNot(_.isExternal)
    .filterNot(v.contains(_))
    .l
    .distinct
  callees.foreach(callee => v += callee)
  callees ++ callees.flatMap(callee => getCallees(callee, v))
}

def make_report(
    flow: Path,
    filename: String,
    sentinel: Option[CfgNode],
    sanitizer: String
): Option[Report] = {
  Try {
    Report(
      filename,
      sanitizer,
      createCodeSnippet(flow)
        .map(_.build(get_basedir(), sentinel))
        .mkString("\n")
    )
  } match {
    case Success(x) => Some(x)
    case Failure(_) => None
  }
}

def save_report(reports: List[Report]): Unit = {
  implicit val formats: Formats = Serialization.formats(NoTypeHints)
  val path =
    Paths.get(Option(System.getenv("OUT_PATH")).getOrElse("joern.json"))
  Files.write(
    path,
    writePretty(reports).getBytes(StandardCharsets.UTF_8),
    StandardOpenOption.CREATE,
    StandardOpenOption.TRUNCATE_EXISTING
  )
}

def run(
    sink: Iterator[CfgNode],
    harness_paths: Set[String],
    label: String
): List[Report] = {
  def dedupKey(flow: Path): (String, Option[CfgNode]) = {
    if (flow.elements.size == 0) {
      return ("", None)
    }

    val sourceFileNames = flow
      .elements
      .filter(_.isInstanceOf[CfgNode])
      .headOption
      .map(_.asInstanceOf[CfgNode].method.typeDecl.filename.l)
      .getOrElse(List[String]())
    val sourceFileName = sourceFileNames.size match {
      case 1 => sourceFileNames(0)
      case _ => ""
    }
    (sourceFileName, Sentinel.get(flow))
  }

  val src = source(harness_paths).l
  val req_gets = request_gets.toSet

  sink
    .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
    .reachableByFlows(src ++ req_gets)
    .l
    .map(p => {
      val node = p.elements.head
      if (node.isInstanceOf[Call] && req_gets.contains(node.asInstanceOf[Call])) {
        node.asInstanceOf[Call].iterator.reachableByFlows(src).l.map(pp =>
          Path(pp.elements.init ++ p.elements)
        )
      } else {
        List(p)
      }
    })
    .flatten
    .map(flow => (flow, dedupKey(flow)))
    .filter(_._2._1 != "")
    .distinctBy(_._2)
    .flatMap(e => make_report(e._1, e._2._1, e._2._2, label))
}

def request_gets(implicit cpg: Cpg) = {
  cpg.call.where(_.callee.fullName(".*Request.*.get.*"))
}

def clojure_lang_hooks(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("clojure.lang.IFn.invoke:.*"))
    .argument
    .argumentIndex(1, 2)
}

def command_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("^java.lang.Process(Builder|Impl).start:.*"))
    .argument
    .argumentIndex(0) ++
    cpg.call
      .where(_.callee.fullName("^hudson.Launcher\\$ProcStarter.start:.*"))
      .argument
      .argumentIndex(0) ++
    cpg.call
      .where(_.callee.fullName("^org.apache.commons.exec.DefaultExecutor.execute:.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("^java.lang.Runtime.exec:.*"))
      .argument
      .argumentIndex(1, 2)
}

def deserialization(implicit cpg: Cpg) = {
  val readSink = cpg.call
    .where(_.callee.fullName(
      "java.io.ObjectInputStream.read(Object|ObjectOverride|Unshared):.*"
    ))
    .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
    .argument
    .argumentIndex(0)
  val initSink = cpg.call
    .where(_.callee.fullName("java.io.ObjectInputStream.<init>:.*"))
    .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
    .argument
    .argumentIndex(1)

  readSink.reachableBy(initSink) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "java.beans.XMLDecoder.readObject:.*",
          "java.rmi.MarshalledObject.get:.*",
          "javax.management.remote.rmi.RMIConnectorServer.start:.*",
          "com.caucho.hessian.io.HessianInput.readObject:.*",
          "flex.messaging.io.amf.Amf3Input.readObject:.*",
        ) *
      ))
      .argument
      .argumentIndex(0) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "org.apache.commons.lang3.SerializationUtils.deserialize:.*",
          "org.springframework.core.serializer.DefaultDeserializer.deserialize:.*",
          "org.springframework.web.util.WebUtils.deserializeFromByteArray:.*",
          "com.thoughtworks.xstream.XStream.fromXML:.*",
          "com.fasterxml.jackson.databind.ObjectMapper.readValue:.*",
          "com.esotericsoftware.kryo.Kryo.readClassAndObject:.*",
          "org.yaml.snakeyaml.Yaml.load:.*",
          "com.owlike.genson.Genson.deserialize:.*",
        ) *
      ))
      .argument
      .argumentIndex(1)
}

def el_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      "jakarta.el.ExpressionFactory.create(Method|Value)Expression:.*"
    ))
    .argument
    .argumentIndex(2) ++
    cpg.call
      .where(_.callee.fullName(
        "javax.validation.ConstraintValidatorContext.buildConstraintViolationWithTemplate:.*"
      ))
      .argument
      .argumentIndex(1)
}

def ldap_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("^javax.naming.directory.(Initial)?DirContext.search:.*"))
    .argument
    .argumentIndex(1, 2)
}

def naming_context_look_up(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("^org.apache.logging.log4j.Logger.(error|fatal|warn|info|debug|trace):.*"))
    .argument
    .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("javax.naming..*Context.lookup(Link)?:.*"))
      .argument
      .argumentIndex(1)
}

def reflective_call(implicit cpg: Cpg) = {
  val sinkArgs = Iterator(
    (
      Set(
        "^java.lang.Class.forName:.*",
        "^java.lang.ClassLoader.loadClass:.*"
      ),
      1
    ),
    (
      Set(
        "^java.lang.Class.forName:.*",
        "^java.lang.ClassLoader.loadClass:.*"
      ),
      2
    ),
    (
      Set(
        "^java.lang.(Runtime|System).load(Library)?:.*",
        "^java.lang.System.mapLibraryName:.*",
        "^java.lang.ClassLoader.findLibrary:.*",
        "^java.lang.Runtime.load:.*",
        "^java.nio.file.Files.(copy|move):.*"
      ),
      1
    )
  )
  sinkArgs.flatMap(e => {
    val methods = e._1
    val argNo = e._2
    cpg.call
      .where(_.callee.fullName(methods.toSeq *))
      .argument
      .argumentIndex(argNo)
      .where(_.typ.fullName("java.lang.String"))
  })
}

def regex_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      List(
        "^java.util.regex.Pattern.(compile|matches):.*",
        "^java.lang.String.(matches|replaceAll|replaceFirst|split):.*"
      ) *
    ))
    .argument
    .argumentIndex(1)
}

def script_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      List(
        "^javax.script.ScriptEngine.eval:.*",
        "^groovy.lang.GroovyShell.evaluate:.*",
        "^org.apache.commons.jexl3.JexlExpression.evaluate:.*",
        "^org.apache.commons.jexl3.JxltEngine.Expression.evaluate:.*",
        "^ognl.Ognl.getValue:.*",
        "^org.apache.commons.ognl.Ognl.getValue:.*",
        "^bsh.Interpreter.(eval|get):.*",
        "^org.springframework.expression.(Spel)?ExpressionParser.parseExpression:.*",
      ) *
    ))
    .argument
    .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "^java.lang.reflect.Method.invoke:.*",
          "^java.lang.ClassLoader.defineClass.define:.*",
          "^javax.tools.JavaCompiler.run:.*",
          "^org.mvel2.MVEL.executeExpression:.*",
          "^org.mozilla.javascript.Context.evaluate(String|Reader):.*",
        ) *
      ))
      .argument
}

def sql_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      "^java.sql.Statement.(execute(Batch|LargeBatch|LargeUpdate|Query|Update)?|createNativeQuery):.*"
    ))
    .argument
    .argumentIndex(1)
}

def ssrf(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      List(
        "java.net.SocketImpl.connect:.*",
        "java.net.Socket.connect:.*",
        "java.net.SocksSocketImpl:.*",
        "java.nio.channels.SocketChannel.connect:.*",
        "sun.nio.ch.SocketAdaptor.connect:.*",
        "jdk.internal.net.http.PlainHttpConnection.connect:.*"
      ) *
    ))
    .argument
    .argumentIndex(1, 2) ++
    cpg.call
      .where(_.callee.fullName("^java.net.http.HttpClient.send:.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("^java.net.Socket.<init>:.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("^java.net.URL.openConnection:.*"))
      .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
      .argument
      .argumentIndex(0)
      .reachableBy(
        cpg.call
          .where(_.callee.fullName("^java.net.URL.<init>:.*"))
          .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
          .argument
          .argumentIndex(1)
      ) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "^org.apache.http.impl.client.CloseableHttpClient.execute:.*",
          "^org.apache.http.impl.nio.client.CloseableHttpAsyncClient.execute:.*",
          "^org.apache.http.client.HttpClient.execute:.*",
          "^org.apache.http.client.fluent.Request.(Get|Patch|Post|Put|Delete).execute:.*",
          "^okhttp3.OkHttpClient.newCall:.*",
          "^org.springframework.web.client.RestTemplate.getForObject:.*",
        ) *
      ))
      .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
      .argument
      .argumentIndex(1)
}

def xpath_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      "^(jenkins.util.xml.XMLUtils.parse|javax.xml.xpath.XPath.(compile|evaluate|evaluateExpression)):.*"
    ))
    .argument
    .argumentIndexGt(0)
}

def arbitrary_file_read_write(implicit cpg: Cpg) = {
  val sinkArgs = Iterator(
    (
      Set(
        "^java.nio.file.Files.newByteChannel:.*",
        "^java.nio.file.Files.newBufferedReader:.*",
        "^java.nio.file.Files.newBufferedWriter:.*",
        "^java.nio.file.Files.readString:.*",
        "^java.nio.file.Files.readAllBytes:.*",
        "^java.nio.file.Files.readAllLines:.*",
        "^java.nio.file.Files.readSymbolicLink:.*",
        "^java.nio.file.Files.write:.*",
        "^java.nio.file.Files.writeString:.*",
        "^java.nio.file.Files.newInputStream:.*",
        "^java.nio.file.Files.newOutputStream:.*",
        "^java.nio.channels.FileChannel.open:.*"
      ),
      1,
      Set("java.nio.file.Path")
    ),
    (
      Set(
        "^java.nio.file.Files.copy:.*",
        "^java.nio.file.Files.move:.*"
      ),
      2,
      Set("java.nio.file.Path")
    ),
    (
      Set(
        "^java.io.FileReader.<init>:.*",
        "^java.io.FileWriter.<init>:.*",
        "^java.io.FileInputStream.<init>:.*",
        "^java.io.FileOutputStream.<init>:.*",
        "^java.io.FileOutputStream.<init>:.*"
      ),
      1,
      Set("java.lang.String", "java.io.File")
    ),
    (
      Set("^java.util.Scanner.<init>:.*"),
      1,
      Set("java.lang.String", "java.nio.file.Path", "java.io.File")
    ),
    (Set("^org.apache.commons.fileupload.FileItem.write:.*"), 1, Set(".*"))
  )
  sinkArgs.flatMap(e => {
    val methods = e._1
    val argNo = e._2
    val types = e._3
    cpg.call
      .where(_.callee.fullName(methods.toSeq *))
      .argument
      .argumentIndex(argNo)
      .where(_.typ.fullName(types.toSeq *))
  }) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "javax.servlet.http.Part.write:.*",
          "org.apache.commons.fileupload.FileItem.write:.*",
          "org.springframework.web.multipart.MultipartFile.transferTo:.*",
        ) *
      ))
      .argument
      .argumentIndex(0, 1) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "org.apache.commons.io.FileUtils.copyInputStreamToFile:.*",
          "java.nio.file.Files.copy:.*"
        ) *
      ))
      .argument
      .argumentIndex(1, 2) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "org.apache.commons.io.FileUtils.readFileToString:.*",
          "org.springframework.core.io.ResourceLoader.getResource:.*",
          "javax.servlet.ServletContext.getResource:.*",
          "javax.servlet.ServletContext.getResourceAsStream:.*",
        ) *
      ))
      .argument
      .argumentIndex(1)
}

def update_semantics = {
  UserSemantic.updateSemanticsFromDir(UserSemantic.get_semantic_dir())
  semantics = DefaultSemantics()
}

def import_cpg = {
  val cpg_path = Option(System.getenv("CPG_PATH")).getOrElse("")
  if (cpg_path.size == 0) {
    println("[E] Environment is not set (CPG_PATH)")
    exit
  }
  importCpg(cpg_path)
}
