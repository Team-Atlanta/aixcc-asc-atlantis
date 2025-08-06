package com.code_intelligence.jazzer.introspector;

import java.io.FileWriter;
import java.util.Arrays;

import java.io.IOException;
import java.util.AbstractMap.SimpleEntry;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.HashMap;
import java.nio.file.Files;
import java.nio.file.Paths;

import com.google.gson.GsonBuilder;

import soot.*;
import soot.jimple.JimpleBody;
import soot.jimple.IntConstant;
import soot.jimple.Stmt;
import soot.toolkits.graph.ExceptionalUnitGraph;
import soot.toolkits.graph.UnitGraph;
import soot.util.cfgcmd.CFGToDotGraph;
import soot.util.dot.DotGraph;

public class StuckBranchAnalyzer {

  final static String EDGEIDFUNCSIG = "com.code_intelligence.jazzer.runtime.CoverageMap: void recordCoverage(int)";

  // NOTE: Perhaps we need to specifically handle sanitizer hooked funcs
  static Set<String> SKIP_PACKAGES = Set.of("java.", "jdk.", "sun.", "javax.", "com.sun");

  private static Integer getEdgeId(Stmt st) {
    if (st.containsInvokeExpr()) {
      /*
       * invokestatic #22 Method
       * com/code_intelligence/jazzer/runtime/CoverageMap.recordCoverage:(I)V
       */
      String calleeSig = st.getInvokeExpr().getMethod().getSignature();
      if (calleeSig.contains(EDGEIDFUNCSIG)) {
        Value arg0Value = st.getInvokeExpr().getArg(0);
        if (!(arg0Value instanceof IntConstant))
          return null;
        return ((IntConstant) arg0Value).value;
      }
    }
    return null;
  }

  private static void dumpMethodGraph(SootMethod sm) {
    if (!sm.getName().equals("fuzzerTestOneInput"))
      return;

    SootClass sc = sm.getDeclaringClass();
    System.out.println("class: " + sc.getName());
    if (sc.getName().endsWith("PipelineCommandUtilFuzzer")) {
      System.out.println("dump graph of " + sm.getSignature());
      JimpleBody body = (JimpleBody) sm.retrieveActiveBody();
      ExceptionalUnitGraph eug = new ExceptionalUnitGraph(body);
      CFGToDotGraph ctdg = new CFGToDotGraph();
      DotGraph dg = ctdg.drawCFG(eug, null);
      dg.plot("test.dot");
    }
  }

  private static Set<Integer> getContainedEdgeIds(SootMethod sm) {
    Set<Integer> edgeIds = new HashSet<Integer>();
    // <init> also does not has active body, not suitable to use this api to filter
    // System.out.println("method: " + sm.getSignature() + ", active body: " +
    // sm.hasActiveBody());

    try {
      JimpleBody body = (JimpleBody) sm.retrieveActiveBody();
      // System.out.println("body: " + body);
      for (Unit u : body.getUnits()) {
        if (!(u instanceof Stmt))
          continue;
        // System.out.println("Stmt: " + u.toString());
        Integer id = getEdgeId((Stmt) u);
        if (id != null)
          edgeIds.add(id);
      }

      // dumpMethodGraph(sm);
    } catch (Exception e) {
      // e.printStackTrace();
      // ystem.out.println("Skip " + sm.getSignature());
    }
    return edgeIds;
  }

  public static class PathInfo {
    Unit lastbr;
    Integer lastExecutedEdgeId;
    Set<Unit> units;

    public PathInfo(Unit lastbr, Integer lastExecEdgeId, Set<Unit> units) {
      this.lastbr = lastbr;
      this.lastExecutedEdgeId = lastExecEdgeId;
      this.units = units;
    }
  }

  private static Map<Integer, BranchSignature> iterateMethod2GetStuckEdgeIds(SootMethod sm, Set<Integer> executedIds, Map<Integer, Set<Integer>> execEdgeIdsOfStuckId) {
    Map<Integer, BranchSignature> stuckBranches = new HashMap<Integer, BranchSignature>();

    try {
      JimpleBody body = (JimpleBody) sm.retrieveActiveBody();
      UnitGraph eug = new ExceptionalUnitGraph(body);
      Queue<SimpleEntry<Unit, PathInfo>> q = new LinkedList<SimpleEntry<Unit, PathInfo>>();

      List<Unit> ul = eug.getHeads();
      for (Unit u : ul) {
        q.add(new SimpleEntry<Unit, PathInfo>(u, new PathInfo(null, null, new HashSet<Unit>())));
      }

      // iterate the q until it is empty
      while (!q.isEmpty()) {
        SimpleEntry<Unit, PathInfo> pair = q.poll();
        Unit cur = pair.getKey();
        PathInfo pathinfo = pair.getValue();
        Unit lastbr = pathinfo.lastbr;
        Integer lastExecEdgeId = pathinfo.lastExecutedEdgeId;
        Set<Unit> units = pathinfo.units;

        // if u is a branch stmt, get the edge id
        // if the edge id is not executed, add it to the stuck edge ids
        // if the edge id is executed, add its previous branch edge id to the q
        if (!(cur instanceof Stmt)) {
          continue;
        }

        // System.out.println("handling stmt: " + cur.toString() + " in method: "
        // + sm.getSignature() + " lastbr: " + lastbr);

        Stmt st = (Stmt) cur;

        if (cur.branches()) {
          lastbr = cur;

        } else if (st.containsInvokeExpr()) {
          Integer edgeId = getEdgeId(st);
          if (edgeId != null) {
            if (!executedIds.contains(edgeId)) {

              if (lastbr == null || lastExecEdgeId == null) {
                // unknown stuck places which is not branch
                // stmt, just ignore it
                // some can be dangling caught exception
                // stmts, the rest leaves unknown
                continue;
              }

              Map.Entry<List<String>, List<String>> sigpair = BranchSignature.getBranchSignature(eug, lastbr);
              if (sigpair == null) {
                throw new RuntimeException("This is impossible");
              }

              stuckBranches.put(edgeId, new BranchSignature(sm.getDeclaringClass().getName(), sm.getName(),
                  sm.getSignature(), lastbr.toString(), sigpair.getKey(), sigpair.getValue()));
              if (execEdgeIdsOfStuckId.get(edgeId) == null) {
                execEdgeIdsOfStuckId.put(edgeId, new HashSet<Integer>());
              }
              execEdgeIdsOfStuckId.get(edgeId).add(lastExecEdgeId);

              // we meet the first stuck edge id, stop exploration
              // in this ctrl flow path
              continue;
            } else {
              // executed one, keep searching
              lastExecEdgeId = edgeId;
            }
          }
        }

        if (units.contains(cur)) {
          // loop detected, stop exploration
          // we still explore this node since we want to explore all edges
          // instead of all nodes
          continue;
        }

        for (Unit succ : eug.getSuccsOf(cur)) {
          // copy the units set and add the current node to it
          Set<Unit> newUnits = new HashSet<Unit>(units);
          newUnits.add(cur);
          q.add(new SimpleEntry<Unit, PathInfo>(succ, new PathInfo(lastbr, lastExecEdgeId, newUnits)));
        }
      }

    } catch (Exception e) {
      // log instead of throw, count as no stuck branch
      System.out.println("Caught error: " + e);
    }

    return stuckBranches;
  }

  public static Map<Integer, BranchSignature> getStuckBranches(Set<Integer> executedIds, Map<Integer, Set<Integer>> execEdgeIdsOfStuckId) {
    // get all methods that have partial coverage (part of the edge ids are
    // executed)
    Map<SootMethod, Set<Integer>> stuckMethods = new HashMap<SootMethod, Set<Integer>>();

    // create a sootclass list
    List<SootClass> scList = new ArrayList<SootClass>();
    for (SootClass sc : Scene.v().getClasses()) {
      scList.add(sc);
    }

    for (SootClass sc : scList) {
      // filter classname in SKIP_PACKAGES
      String fullSCName = sc.getName();
      boolean skip = false;
      for (String pkg : SKIP_PACKAGES) {
        if (fullSCName.startsWith(pkg)) {
          skip = true;
          break;
        }
      }
      if (skip)
        continue;

      List<SootMethod> smList = new ArrayList<SootMethod>();
      for (SootMethod sm : sc.getMethods()) {
        smList.add(sm);
      }
      for (SootMethod sm : smList) {
        if (sm.isPhantom())
          continue;

        // if (!(fullSCName.contains("PipelineCommandUtilFuzzer") &&
        // sm.getName().equals("fuzzerTestOneInput")))
        // continue;

        Set<Integer> ids = getContainedEdgeIds(sm);
        // if (ids.size() > 0)
        // System.out.println("method: " + sm.getSignature() + ", edge ids:"
        // + ids);

        boolean hasID = ids.size() > 0;
        boolean partiallyExecuted = false;
        if (executedIds.containsAll(ids))
          partiallyExecuted = false;
        else
          partiallyExecuted = ids.stream().anyMatch(executedIds::contains);

        // System.out.println("method: " + sm.getSignature() + ", hasID: " +
        // hasID
        // + ", partiallyExecuted: " + partiallyExecuted);
        if (hasID && partiallyExecuted) {
          // not executed edge Ids
          ids.removeAll(executedIds);
          stuckMethods.put(sm, ids);
        }
      }
    }

    // print stuck methods & its uncovered edge ids
    for (Map.Entry<SootMethod, Set<Integer>> entry : stuckMethods.entrySet()) {
      SootMethod sm = entry.getKey();
      Set<Integer> ids = entry.getValue();
      System.out.println("Method: " + sm.getSignature() + " has uncovered edge ids: " + ids);
    }

    // filter the edge id, only left the just uncovered edge ids & the edge id of
    // its
    // previous branch

    Map<Integer, BranchSignature> stuckBranches = new HashMap<Integer, BranchSignature>();

    for (Map.Entry<SootMethod, Set<Integer>> entry : stuckMethods.entrySet()) {
      SootMethod sm = entry.getKey();
      Map<Integer, BranchSignature> _stuckBranches = iterateMethod2GetStuckEdgeIds(sm, executedIds, execEdgeIdsOfStuckId);
      // System.out.println("Method: " + sm.getSignature() + " has stuck edge
      // ids:" + _stuckBranches);
      System.out.println("Method: " + sm.getSignature() + " has " + _stuckBranches.size() + " stuck edge ids ");

      stuckBranches.putAll(_stuckBranches);
    }

    // return these edge id pair <executed branch edge id, its uncovered edge id,
    // true/false branch>
    // also func info etc to retrieve the specific dict

    return stuckBranches;
  }

  private static void analyzeStuckBranches(Set<Integer> executedIds, String dumpFile) {
    // Set<Integer> executedIds = new HashSet<>(Arrays.asList(33, 34, 55));

    Map<Integer, Set<Integer>> execEdgeIdsOfStuckId = new HashMap<Integer, Set<Integer>>();
    Map<Integer, BranchSignature> stuckBranches = getStuckBranches(executedIds, execEdgeIdsOfStuckId);

    //// print stuck branches
    // for (Map.Entry<Integer, BranchSignature> entry : stuckBranches.entrySet()) {
    // Integer edgeId = entry.getKey();
    // BranchSignature bi = entry.getValue();
    // System.out.println("EdgeId: " + edgeId + ", BranchSignature: " +
    //// bi.toJson());
    // }

    Map<String, Object> output = new HashMap<>();
    output.put("stuckBranches", stuckBranches);
    output.put("execEdgeIdsOfStuckId", execEdgeIdsOfStuckId);

    // dump the stuck branches (purely in json) to a file
    try {
      String json = new GsonBuilder().setPrettyPrinting().create().toJson(output);
      FileWriter fw = new FileWriter(dumpFile);
      fw.write(json);
      fw.close();

    } catch (IOException e) {
      e.printStackTrace();
    }
  }

  public static void analyze(String edgeIDFile, String dumpFile) {
    // use gson to load a json file which is a IntrospectionData
    // IntrospectionData.JsonData introspectionData = new
    // GsonBuilder().create().fromJson("/data/zhangcen/workspace/llmsec/java_dict_generator/introspection.json",
    // IntrospectionData.JsonData.class);

    // parses introspection.json, which has an integer per line
    // read the file
    // edgeIDFile ->
    // "/data/zhangcen/workspace/llmsec/java_dict_generator/introspection.json"
    List<String> lines = null;
    try {
      lines = Files.readAllLines(Paths.get(edgeIDFile));
    } catch (IOException e) {
      e.printStackTrace();
    }
    // parse them into a set<integer>
    Set<Integer> allEdgeIds = new HashSet<Integer>();
    for (String line : lines) {
      allEdgeIds.add(Integer.parseInt(line.strip()));
    }

    // print alledgeids length
    System.out.println("allEdgeIds length: " + allEdgeIds.size());

    analyzeStuckBranches(allEdgeIds, dumpFile);
  }
}
