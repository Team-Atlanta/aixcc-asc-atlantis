import io.shiftleft.semanticcpg.language._
import io.shiftleft.codepropertygraph.Cpg

def findMainMethods(): List[Method] = {
  cpg.method.l
}


var mainMethods = findMainMethods()
mainMethods.toJson #> "<output>"
