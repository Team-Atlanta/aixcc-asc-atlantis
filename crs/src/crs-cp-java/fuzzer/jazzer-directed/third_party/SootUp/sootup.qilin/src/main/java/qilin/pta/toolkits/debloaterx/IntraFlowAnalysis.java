package qilin.pta.toolkits.debloaterx;

import java.util.HashSet;
import java.util.Queue;
import java.util.Set;
import qilin.core.builder.MethodNodeFactory;
import qilin.core.pag.*;
import qilin.util.PTAUtils;
import qilin.util.Pair;
import qilin.util.queue.QueueReader;
import qilin.util.queue.UniqueQueue;
import sootup.core.jimple.basic.Local;
import sootup.core.jimple.basic.Value;
import sootup.core.jimple.common.constant.NullConstant;
import sootup.core.jimple.common.expr.AbstractInstanceInvokeExpr;
import sootup.core.jimple.common.expr.AbstractInvokeExpr;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.model.SootMethod;
import sootup.core.signatures.MethodSubSignature;
import sootup.core.types.ArrayType;
import sootup.core.types.ClassType;
import sootup.core.types.ReferenceType;
import sootup.core.types.Type;

/*
 * Implementation of Algorithm 3 and Fig 10 in the paper.
 * */
public class IntraFlowAnalysis {
  private final PAG pag;
  private final XUtility utility;
  private final SootMethod method;
  protected final XPAG xpag;
  protected final Set<LocalVarNode> params = new HashSet<>();

  public IntraFlowAnalysis(XUtility utility, SootMethod method) {
    this.utility = utility;
    this.pag = utility.getPta().getPag();
    this.method = method;
    this.xpag = utility.getXpag();
    collectParams();
  }

  protected void collectParams() {
    MethodPAG srcmpag = pag.getMethodPAG(method);
    MethodNodeFactory srcnf = srcmpag.nodeFactory();
    VarNode thisNode = srcnf.caseThis();
    // handle parameters
    for (int i = 0; i < method.getParameterCount(); ++i) {
      if (method.getParameterType(i) instanceof ReferenceType
          && !PTAUtils.isPrimitiveArrayType(method.getParameterType(i))) {
        LocalVarNode param = (LocalVarNode) srcnf.caseParm(i);
        this.params.add(param);
      }
    }
    this.params.add((LocalVarNode) thisNode);
  }

  //////////////////////////////////////////////////////////////////////////////////
  /*
   * x = y = z = ... = node;
   * */
  Set<Node> epsilon(Node node) {
    Queue<Node> queue = new UniqueQueue<>();
    for (Edge edge : xpag.getOutEdges(node)) {
      queue.add(edge.to);
    }
    Set<Node> visit = new HashSet<>();
    while (!queue.isEmpty()) {
      Node front = queue.poll();
      visit.add(front);
      for (Edge edge : xpag.getOutEdges(front)) {
        if (edge.kind == EdgeKind.ASSIGN && !visit.contains(edge.to)) {
          queue.add(edge.to);
        }
      }
    }
    return visit;
  }

  /*
   * t = new T;
   * x = ... = t;
   * return x;
   * */
  public boolean isDirectlyReturnedHeap(AllocNode heap) {
    Set<Node> visit = epsilon(heap);
    boolean flag = false;
    for (Node node : visit) {
      if (node instanceof LocalVarNode) {
        LocalVarNode lvn = (LocalVarNode) node;
        if (lvn.isReturn()) {
          flag = true;
        }
      }
    }
    return flag;
  }

  public boolean isContentFromParam(AllocNode heap) {
    Type heapType = heap.getType();
    if (heapType instanceof ClassType) {
      return isInstanceObjectContentFromParam(heap);
    } else {
      return isArrayContentFromParam(heap);
    }
  }

  /*
   * return true iff heap.f comes from any parameter of heap.getMethod().
   * */
  private boolean isInstanceObjectContentFromParam(AllocNode heap) {
    Set<Node> paramInArgs = collectParamInArguments(heap);
    if (paramInArgs.isEmpty()) {
      return false;
    }
    Queue<Node> queue = new UniqueQueue<>();
    Set<Node> visited = new HashSet<>();
    queue.addAll(params);
    while (!queue.isEmpty()) {
      Node front = queue.poll();
      if (paramInArgs.contains(front)) {
        return true;
      }
      visited.add(front);
      for (Edge edge : xpag.getOutEdges(front)) {
        if (edge.kind == EdgeKind.ASSIGN
            || edge.kind == EdgeKind.CLOAD
            || edge.kind == EdgeKind.LOAD) {
          if (!visited.contains(edge.to)) {
            queue.add(edge.to);
          }
        }
      }
    }
    return false;
  }

  private Set<Node> collectParamInArguments(AllocNode heap) {
    ClassType type = (ClassType) heap.getType();
    Set<Node> x = epsilon(heap);
    Set<Node> ret = new HashSet<>();
    HeapContainerQuery hcq = this.utility.getHCQ(heap);
    Set<LocalVarNode> inParams = hcq.getInParamsToCSFields();
    MethodPAG srcmpag = pag.getMethodPAG(method);
    for (final Stmt s : srcmpag.getInvokeStmts()) {
      AbstractInvokeExpr ie = s.getInvokeExpr();
      if (!(ie instanceof AbstractInstanceInvokeExpr)) {
        continue;
      }
      AbstractInstanceInvokeExpr iie = (AbstractInstanceInvokeExpr) ie;
      Local base = iie.getBase();
      LocalVarNode receiver = pag.findLocalVarNode(method, base, base.getType());
      if (!x.contains(receiver)) {
        continue;
      }
      int numArgs = ie.getArgCount();
      Value[] args = new Value[numArgs];
      for (int i = 0; i < numArgs; i++) {
        Value arg = ie.getArg(i);
        if (!(arg.getType() instanceof ReferenceType) || arg instanceof NullConstant) {
          continue;
        }
        args[i] = arg;
      }
      MethodSubSignature subSig = iie.getMethodSignature().getSubSignature();
      VirtualCallSite virtualCallSite =
          new VirtualCallSite(
              receiver,
              s,
              new ContextMethod(method, utility.getPta().emptyContext()),
              iie,
              subSig,
              qilin.core.builder.callgraph.Edge.ieToKind(iie));
      QueueReader<SootMethod> targets = pag.getCgb().dispatch(type, virtualCallSite);
      while (targets.hasNext()) {
        SootMethod target = targets.next();
        MethodPAG tgtmpag = pag.getMethodPAG(target);
        MethodNodeFactory tgtnf = tgtmpag.nodeFactory();
        int numParms = target.getParameterCount();
        if (numParms != numArgs) {
          System.out.println(target);
        }
        for (int i = 0; i < numParms; i++) {
          if (target.getParameterType(i) instanceof ReferenceType) {
            if (args[i] != null) {
              ValNode argNode = pag.findValNode(args[i], method);
              if (argNode instanceof LocalVarNode) {
                LocalVarNode lvn = (LocalVarNode) argNode;
                LocalVarNode param = (LocalVarNode) tgtnf.caseParm(i);
                if (inParams.contains(param)) {
                  ret.add(lvn);
                }
              }
            }
          }
        }
      }
    }
    return ret;
  }

  /*
   * x = new T[]
   * x[i] = param.*;
   * */
  private boolean isArrayContentFromParam(AllocNode heap) {
    if (!(heap.getType() instanceof ArrayType)) {
      return false;
    }
    Set<Node> x = epsilon(heap);
    Queue<Node> queue = new UniqueQueue<>();
    Set<Node> visited = new HashSet<>();
    queue.addAll(params);
    while (!queue.isEmpty()) {
      Node front = queue.poll();
      visited.add(front);
      for (Edge edge : xpag.getOutEdges(front)) {
        if (edge.kind == EdgeKind.ASSIGN
            || edge.kind == EdgeKind.CLOAD
            || edge.kind == EdgeKind.LOAD) {
          if (!visited.contains(edge.to)) {
            queue.add(edge.to);
          }
        }
        if (edge.kind == EdgeKind.STORE) {
          if (x.contains(edge.to)) {
            return true;
          }
        }
      }
    }
    return false;
  }

  private State nextState(State currState, EdgeKind kind) {
    switch (currState) {
      case O:
        {
          if (kind == EdgeKind.NEW) {
            return State.VPlus;
          }
        }
      case VPlus:
        {
          if (kind == EdgeKind.ASSIGN) {
            return State.VPlus;
          } else if (kind == EdgeKind.STORE) {
            return State.VMinus;
          }
        }
      case VMinus:
        {
          if (kind == EdgeKind.IASSIGN) {
            return State.VMinus;
          } else if (kind == EdgeKind.ILOAD) {
            return State.VMinus;
          } else if (kind == EdgeKind.INEW) {
            return State.O;
          }
        }
    }
    return State.Error;
  }

  /*
   * implementation of nextNodeStates in Algorithm 3 in the paper. It also encodes Fig 10 in the paper.
   * */
  private Set<Pair<Node, State>> getNextNodeStates(
      Pair<Node, State> nodeState, Set<Node> thisAlias, Set<SparkField> stFields) {
    Node node = nodeState.getFirst();
    State state = nodeState.getSecond();
    Set<Pair<Node, State>> ret = new HashSet<>();
    for (Edge edge : xpag.getOutEdges(node)) {
      State nextState = nextState(state, edge.kind);
      if (nextState != State.Error) {
        if (edge.kind == EdgeKind.STORE && thisAlias.contains(edge.to)) {
          Type type = edge.field.getType();
          if (!utility.isCoarseType(type)) {
            continue;
          }
          stFields.add(edge.field);
        } else if (edge.kind == EdgeKind.ILOAD && thisAlias.contains(edge.to)) {
          Type type = edge.field.getType();
          if (!utility.isCoarseType(type)) {
            continue;
          }
          stFields.add(edge.field);
        } else {
          ret.add(new Pair<>(edge.to, nextState));
        }
      }
    }
    return ret;
  }

  /*
   * Implementation of Algorithm 3 in the paper.
   * */
  public Set<SparkField> retrieveStoreFields(AllocNode heap) {
    Set<SparkField> ret = new HashSet<>();
    MethodPAG srcmpag = pag.getMethodPAG(method);
    MethodNodeFactory srcnf = srcmpag.nodeFactory();
    VarNode thisNode = srcnf.caseThis();
    Set<Node> thisAlias = epsilon(thisNode);
    Queue<Pair<Node, State>> queue = new UniqueQueue<>();
    Set<Pair<Node, State>> visited = new HashSet<>();
    queue.add(new Pair<>(heap, State.O));
    while (!queue.isEmpty()) {
      Pair<Node, State> front = queue.poll();
      visited.add(front);
      Set<Pair<Node, State>> nextStates = getNextNodeStates(front, thisAlias, ret);
      for (Pair<Node, State> nextState : nextStates) {
        if (!visited.contains(nextState)) {
          queue.add(nextState);
        }
      }
    }
    return ret;
  }
}
