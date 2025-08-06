package com.code_intelligence.jazzer.introspector;

import java.util.AbstractMap;
import java.util.HashSet;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.Map;

import java.util.function.Predicate;
import java.util.function.Function;
import java.util.stream.Stream;

import soot.*;
import soot.jimple.Stmt;
import soot.jimple.JimpleBody;
import soot.toolkits.graph.UnitGraph;
import soot.toolkits.graph.ExceptionalUnitGraph;

import com.google.gson.GsonBuilder;

public class BranchSignature {

  final static String JAZZER_INSTRUMENTED_PKG = "com.code_intelligence.jazzer.runtime";

  final static int BRANCH_ID_DEPTH = 2;

  public String className;

  public String methodName;

  public String methodSignature;

  public String stmt;

  public Set<String> preds;

  public Set<String> succs;

  public BranchSignature(String className, String methodName, String methodSignature, String stmt, List<String> preds,
      List<String> succs) {
    this.className = className;
    this.methodName = methodName;
    this.methodSignature = methodSignature;
    this.stmt = stmt;
    this.preds = new HashSet<String>(preds);
    this.succs = new HashSet<String>(succs);
  }

  public String toJson() {
    return new GsonBuilder().setPrettyPrinting().create().toJson(this);
  }

  public String toString() {
    return toJson();
  }

  private static boolean isJazzerInstrumented(Stmt st) {
    if (st.containsInvokeExpr()) {
      String calleeSig = st.getInvokeExpr().getMethod().getSignature();
      if (calleeSig.contains(JAZZER_INSTRUMENTED_PKG))
        return true;
    }
    return false;
  }

  /*
   * get the real preds (x layers) of a unit, not including the jazzer
   * instrumented
   */
  private static List<Unit> getRealPred(UnitGraph ug, Unit u, int depth) {
    List<Unit> preds = new ArrayList<Unit>();

    if (depth <= 0)
      return preds;

    for (Unit pred : ug.getPredsOf(u)) {
      if (!(pred instanceof Stmt))
        continue;

      if (!isJazzerInstrumented((Stmt) pred)) {
        preds.add(pred);
        for (Unit pred2 : getRealPred(ug, pred, depth - 1)) {
          preds.add(pred2);
        }
      } else {
        for (Unit pred2 : getRealPred(ug, pred, depth)) {
          preds.add(pred2);
        }
      }
    }

    return preds;
  }

  /*
   * get the real succs (x layers) of a unit, not including the jazzer
   * instrumented
   */
  private static List<Unit> getRealSucc(UnitGraph ug, Unit u, int depth) {
    List<Unit> succs = new ArrayList<Unit>();

    if (depth <= 0)
      return succs;

    for (Unit succ : ug.getSuccsOf(u)) {
      if (!(succ instanceof Stmt))
        continue;

      if (!isJazzerInstrumented((Stmt) succ)) {
        succs.add(succ);
        for (Unit succ2 : getRealSucc(ug, succ, depth - 1)) {
          succs.add(succ2);
        }
      } else {
        for (Unit succ2 : getRealSucc(ug, succ, depth)) {
          succs.add(succ2);
        }
      }
    }

    return succs;
  }

  public static Map.Entry<List<String>, List<String>> getBranchSignature(UnitGraph ug, Unit br) {
    if (!br.branches())
      return null;

    // collect all direct preds (not including the jazzer instrumented)
    List<String> preds = new ArrayList<String>();
    for (Unit pred : getRealPred(ug, br, BRANCH_ID_DEPTH)) {
      preds.add(pred.toString());
    }

    // collect all direct succs (not including the jazzer instrumented)
    List<String> succs = new ArrayList<String>();
    for (Unit succ : getRealSucc(ug, br, BRANCH_ID_DEPTH)) {
      succs.add(succ.toString());
    }

    // System.out.println("-----");
    //// print preds
    // for (Unit pred : preds) {
    // System.out.println("Pred: " + pred.toString());
    // }
    // System.out.println("Branch stmt: " + br.toString());
    // for (Unit succ : succs) {
    // System.out.println("Succ: " + succ.toString());
    // }
    // System.out.println("-----");

    return new AbstractMap.SimpleEntry<List<String>, List<String>>(preds, succs);
  }

  private static SootMethod findTargetMethod(String targetClass, String methodSignature) {
    for (SootClass sc : Scene.v().getClasses()) {
      String fullSCName = sc.getName();
      if (fullSCName.equals(targetClass) || fullSCName.endsWith("." + targetClass)) {
        for (SootMethod _sm : sc.getMethods()) {
          if (_sm.getSignature().equals(methodSignature)) {
            return _sm;
          }
        }
      }
    }
    return null;
  }

  /*
   * bs1 should be the instrumented branch signature, bs2 should be the original
   * branch
   */
  public static float getSimilarity(BranchSignature bs1, BranchSignature bs2) {
    // Our Strategy: the strings of all stmts which do not contain the
    // JAZZER_INSTRUMENTED_PKG should be the same

    // NOTE: there may have multiple matched branches since the signature is not
    // 100%
    // accurate (stmt strings can differ before/after instrumentation), we just pick
    // the
    // first matched one here

    Predicate<String> notContainJAZZER = s -> !s.contains(JAZZER_INSTRUMENTED_PKG);
    Function<BranchSignature, Set<String>> getStmts = bs -> Stream
        .of(bs.preds, Collections.singleton(bs.stmt), bs.succs).flatMap(Collection::stream).filter(notContainJAZZER)
        .collect(Collectors.toSet());

    Set<String> bs1Stmts = getStmts.apply(bs1);
    Set<String> bs2Stmts = getStmts.apply(bs2);

    //// print the following three boolean values
    // System.out.println("COMP: " + bs1.className.equals(bs2.className) + " "
    // + bs1.methodSignature.equals(bs2.methodSignature) + " "
    // + bs1Stmts.equals(bs2Stmts));

    //// bs1stmts
    // System.out.println("bs1Stmts: ");
    // for (String s : bs1Stmts) {
    // System.out.println(s);
    // }
    //// bs2stmts
    // System.out.println("bs2Stmts: ");
    // for (String s : bs2Stmts) {
    // System.out.println(s);
    // }

    float similarity = 0.0f;

    if (!bs1.className.equals(bs2.className))
      return similarity;
    if (!bs1.methodSignature.equals(bs2.methodSignature))
      return similarity;

    // calculate the similarity: # of bs1 stmts in bs2 stmts / # of bs1 stmts
    int count = 0;
    for (String s : bs1Stmts) {
      if (bs2Stmts.contains(s)) {
        count++;
      }
    }
    similarity = (float) count / bs1Stmts.size();

    return similarity;
  }

  public static Unit locateBranchBySignature(BranchSignature bs) {
    SootMethod sm = findTargetMethod(bs.className, bs.methodSignature);
    if (sm == null) {
      // log instead of throw
      System.out.println("Cannot find the target method: " + bs.className + " in class: " + bs.methodSignature);
      return null;
    }

    try {
      JimpleBody body = (JimpleBody) sm.retrieveActiveBody();
      UnitGraph eug = new ExceptionalUnitGraph(body);

      List<Unit> branches = new ArrayList<Unit>();

      for (Unit u : eug) {
        if (u.branches()) {
          branches.add(u);
        }
      }

      float maxSimilarity = 0.0f;
      Unit mostMatched = null;

      for (Unit br : branches) {
        Map.Entry<List<String>, List<String>> sig = getBranchSignature(eug, br);
        if (sig == null)
          // impossible here
          continue;

        BranchSignature bs2 = new BranchSignature(bs.className, bs.methodName, bs.methodSignature, br.toString(),
            sig.getKey(), sig.getValue());

        // if (bs.methodSignature.contains("doexecCommandUtils")) {
        // // print the branch signature about to compare
        // System.out.println("-------");
        // System.out.println("bs1: " + bs.toString());
        // System.out.println("bs2: " + bs2.toString());
        // System.out.println("-------");
        // }

        float similarity = getSimilarity(bs, bs2);
        if (mostMatched == null || similarity > maxSimilarity) {
          maxSimilarity = similarity;
          mostMatched = br;
        }
      }

      return mostMatched;
    } catch (Exception e) {
      // log instead of throw, count as not found
      System.out.println("Caught error in locateBranchBySignature: " + e.getMessage());
      return null;
    }
  }

}
