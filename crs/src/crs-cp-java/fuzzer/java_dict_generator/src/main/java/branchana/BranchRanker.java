package branchana;

import java.io.IOException;
import java.util.AbstractMap.SimpleEntry;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Iterator;
import java.util.Set;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.HashMap;
import java.nio.file.Files;
import java.nio.file.Paths;

import com.google.gson.GsonBuilder;

import java.lang.reflect.Type;
import com.google.gson.reflect.TypeToken;

import soot.*;
import soot.jimple.JimpleBody;
import soot.jimple.Stmt;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.jimple.toolkits.ide.icfg.JimpleBasedInterproceduralCFG;
import soot.toolkits.graph.ExceptionalUnitGraph;
import soot.toolkits.graph.UnitGraph;

public class BranchRanker {
	static Map<String, Set<String>> SANITIZER_FUNCS = new HashMap<String, Set<String>>() {
		{
			// OS command injection
			put("java.lang.ProcessImpl", new HashSet<String>() {
				{
					add("start");
				}
			});
			// Deserialization
			put("java.io.ObjectInputStream", new HashSet<String>() {
				{
					add("<init>");
					add("readObject");
					add("readObjectOverride");
					add("readUnshared");
				}
			});
			// Expression Language Injection
			put("javax.el.ExpressionFactory", new HashSet<String>() {
				{
					add("createValueExpression");
					add("createMethodExpression");
				}
			});
			put("jakarta.el.ExpressionFactory", new HashSet<String>() {
				{
					add("createValueExpression");
					add("createMethodExpression");
				}
			});
			put("javax.validation.ConstraintValidatorContext", new HashSet<String>() {
				{
					add("buildConstraintViolationWithTemplate");
				}
			});
			// FileReadWrite & FileSystemTraversal
			put("java.nio.file.Files", new HashSet<String>() {
				{
					add("newByteChannel");
					add("newBufferedReader");
					add("newBufferedWriter");
					add("readString");
					add("readAllBytes");
					add("readAllLines");
					add("readSymbolicLink");
					add("write");
					add("writeString");
					add("newInputStream");
					add("newOutputStream");
					add("copy");
					add("move");
				}
			});
			put("java.nio.channels.FileChannel", new HashSet<String>() {
				{
					add("open");
				}
			});
			put("java.io.FileReader", new HashSet<String>() {
				{
					add("<init>");
				}
			});
			put("java.io.FileWriter", new HashSet<String>() {
				{
					add("<init>");
				}
			});
			put("java.io.FileInputStream", new HashSet<String>() {
				{
					add("<init>");
				}
			});
			put("java.io.FileOutputStream", new HashSet<String>() {
				{
					add("<init>");
				}
			});
			put("java.util.Scanner", new HashSet<String>() {
				{
					add("<init>");
				}
			});
			// we skip IntegerOverflow
			// JenkinsXss
			put("hudson.AbstractMarkupText", new HashSet<String>() {
				{
					add("addMarkup");
					add("toString");
				}
			});
			// LdapInjection
			put("javax.naming.directory.DirContext", new HashSet<String>() {
				{
					add("search");
				}
			});
			// NamingContextLookup
			put("javax.naming.Context", new HashSet<String>() {
				{
					add("lookup");
					add("lookupLink");
				}
			});
			// ReflectiveCall
			put("java.lang.Class", new HashSet<String>() {
				{
					add("forName");
				}
			});
			put("java.lang.ClassLoader", new HashSet<String>() {
				{
					add("loadClass");
					add("findLibrary");
				}
			});
			put("java.lang.Runtime", new HashSet<String>() {
				{
					add("load");
					add("loadLibrary");
				}
			});
			put("java.lang.System", new HashSet<String>() {
				{
					add("load");
					add("loadLibrary");
					add("mapLibraryName");
				}
			});
			// RegexInjection
			put("java.util.regex.Pattern", new HashSet<String>() {
				{
					add("compile");
					add("matches");
				}
			});
			put("java.lang.String", new HashSet<String>() {
				{
					add("matches");
					add("replaceAll");
					add("replaceFirst");
					add("split");
				}
			});
			// ScriptEngineInjection
			put("javax.script.ScriptEngine", new HashSet<String>() {
				{
					add("eval");
				}
			});
			// ServerSideRequestForgery
			put("java.net.SocketImpl", new HashSet<String>() {
				{
					add("connect");
				}
			});
			put("java.nio.channels.SocketChannel", new HashSet<String>() {
				{
					add("connect");
				}
			});
			// SqlInjection
			put("java.sql.Statement", new HashSet<String>() {
				{
					add("execute");
					add("executeBatch");
					add("executeLargeBatch");
					add("executeLargeUpdate");
					add("executeQuery");
					add("executeUpdate");
					add("createNativeQuery");
				}
			});
			// XPathInjection
			put("javax.xml.xpath.XPath", new HashSet<String>() {
				{
					add("compile");
					add("evaluate");
					add("evaluateExpression");
				}
			});
		}
	};

	public static class WalkPath {
		public int callNO;
		public int branchNO;

		public WalkPath(int callNO, int branchNO) {
			this.callNO = callNO;
			this.branchNO = branchNO;
		}

		public String toString() {
			return "<callNO: " + callNO + ", branchNO: " + branchNO + ">";
		}

		static public int calcDistance(WalkPath wp) {
			if (wp.callNO != Integer.MAX_VALUE && wp.branchNO != Integer.MAX_VALUE)
				// TODO: perhaps can be refined
				return wp.callNO + wp.branchNO;
			else
				return Integer.MAX_VALUE;
		}
	}

	private static boolean isSanitizerFunction(SootMethod sm) {
		// callee can be zero, in this case, we can only ignore the handling of this call
		if (sm == null)
			return false;

		// check its signature is in the sanitizer list
		String className = sm.getDeclaringClass().getName();
		String methodName = sm.getName();
		for (Map.Entry<String, Set<String>> entry : SANITIZER_FUNCS.entrySet()) {
			String key = entry.getKey();
			Set<String> value = entry.getValue();
			if (className.equals(key) && value.contains(methodName))
				return true;
		}

		return false;
	}

	private static HashMap<String, Integer> cacheResults = new HashMap<String, Integer>();
	private static int MAX_DEPTH = 15;

	private static Integer calcFuncLevelDistance(CallGraph cg, SootMethod sm) {
		if (cacheResults.containsKey(sm.getSignature())) {
			return cacheResults.get(sm.getSignature());
		}

		Integer distance = Integer.MAX_VALUE;
		Set<SootMethod> lastLayerOfCallees = new HashSet<SootMethod>();
		Set<SootMethod> curLayerOfCallees = new HashSet<SootMethod>();
		curLayerOfCallees.add(sm);

		outerLoop: for (int depth = 1; depth < MAX_DEPTH; depth++) {
			Set<SootMethod> nextLayerOfCallees = new HashSet<SootMethod>();
			for (SootMethod callee : curLayerOfCallees) {
				Iterator<Edge> iter = cg.edgesOutOf(callee);
				while (iter.hasNext()) {
					Edge e = iter.next();
					SootMethod tgt = e.tgt();
					if (isSanitizerFunction(tgt)) {
						// target reached, return the minimum distance
						distance = depth;
						break outerLoop;
					}
					nextLayerOfCallees.add(tgt);
				}
			}

			lastLayerOfCallees = curLayerOfCallees;
			curLayerOfCallees = nextLayerOfCallees;
		}

		cacheResults.put(sm.getSignature(), distance);
		return distance;
	}

	public static class CallInfo {
		public SootMethod sm;
		public Integer brDistance;

		public CallInfo(SootMethod sm, Integer brDistance) {
			this.sm = sm;
			this.brDistance = brDistance;
		}
	}

	private static List<WalkPath> calculateBranchDistance(JimpleBasedInterproceduralCFG icfg,
			SootMethod sm, Unit entry) {
		List<CallInfo> allCalls = new ArrayList<CallInfo>();

		Queue<SimpleEntry<Unit, Integer>> q = new LinkedList<SimpleEntry<Unit, Integer>>();

		CallGraph cg = Scene.v().getCallGraph();
		JimpleBody body = (JimpleBody) sm.retrieveActiveBody();
		UnitGraph eug = new ExceptionalUnitGraph(body);

		// System.out.println("entering method " + sm);
		// Integer distance1 = calcFuncLevelDistance(cg, sm);
		// System.out.println("sm: " + sm + ", distance: " + distance1);

		q.add(new SimpleEntry<Unit, Integer>(entry, 0));

		Set<Unit> units = new HashSet<Unit>();

		// iterate the q until it is empty to get all Calls starting from the entry can
		// reach
		while (!q.isEmpty()) {
			SimpleEntry<Unit, Integer> pair = q.poll();
			Unit cur = pair.getKey();
			Integer brDistance = pair.getValue();

			if (units.contains(cur)) {
				// loop detected, stop exploration
				// we do not explore this node since we want to explore all nodes
				// instead of all edges
				continue;
			}

			units.add(cur);

			// cur is not the target, keep searching, add succs
			if (cur.branches()) {
				brDistance += 1;
			}

			if (icfg.isCallStmt(cur)) {

				List<SootMethod> callees =
						new ArrayList<>(icfg.getCalleesOfCallAt(cur));
				if (callees.size() == 0) {
					SootMethod callee =
							((Stmt) cur).getInvokeExpr().getMethod();
					callees.add(callee);
				}

				for (SootMethod callee : callees) {
					allCalls.add(new CallInfo(callee, brDistance));
				}

			}

			for (Unit succ : eug.getSuccsOf(cur)) {
				q.add(new SimpleEntry<Unit, Integer>(succ, brDistance));
			}
		}

		// System.out.println("exiting method " + sm);
		for (CallInfo ci : allCalls) {
			Integer distance = calcFuncLevelDistance(cg, ci.sm);
			if (distance != Integer.MAX_VALUE)
				System.out.println("call: " + ci.sm + ", br distance: "
						+ ci.brDistance + ", distance: " + distance);
		}

		System.out.println("Calculating func level distances");

		List<WalkPath> allWPs = new ArrayList<WalkPath>();
		for (CallInfo ci : allCalls) {
			Integer distance = calcFuncLevelDistance(cg, ci.sm);
			allWPs.add(new WalkPath(ci.brDistance, distance));
		}

		return allWPs;
	}

	private static SootMethod findTargetMethod(String targetClass, String methodSignature) {
		for (SootClass sc : Scene.v().getClasses()) {
			String fullSCName = sc.getName();
			if (fullSCName.equals(targetClass)
					|| fullSCName.endsWith("." + targetClass)) {
				for (SootMethod _sm : sc.getMethods()) {
					if (_sm.getSignature().equals(methodSignature)) {
						return _sm;
					}
				}
			}
		}
		return null;
	}

	private static void rankGivenBranches(String stuckBranchFile, String rankedBranchFile) {
		JimpleBasedInterproceduralCFG icfg = new JimpleBasedInterproceduralCFG(true);

		// 1. locate the branch based on the signature (they are source points)
		// load the file content to json

		Map<Integer, BranchSignature> branchEntries = null;

		try {
			String json = new String(Files.readAllBytes(Paths.get(stuckBranchFile)));
			Type type = new TypeToken<Map<Integer, BranchSignature>>() {}.getType();
			branchEntries = new GsonBuilder().create().fromJson(json, type);

		} catch (IOException e) {
			e.printStackTrace();
		}

		// 2. rank these branches based on their distances to the target sanitizer functions
		// (they are sink points)
		Map<Integer, Integer> distancesMap = new HashMap<Integer, Integer>();

		for (Map.Entry<Integer, BranchSignature> entry : branchEntries.entrySet()) {
			Integer edgeId = entry.getKey();
			BranchSignature bs = entry.getValue();
			SootMethod sm = findTargetMethod(bs.className, bs.methodSignature);
			if (sm == null) {
				System.out.println("Cannot find the target method: " + bs.className
						+ "." + bs.methodSignature);
				continue;
			}

			Unit br = BranchSignature.locateBranchBySignature(bs);
			if (br != null)
				System.out.println("located branch: " + br + " in method: "
						+ sm.getSignature() + ", edgeId: " + edgeId);
			else {
				System.out.println("Cannot locate the branch in method: "
						+ sm.getSignature() + ", edgeId: " + edgeId);
				// TODO: for some reasons it fails to locate, just skip it
				continue;
			}

			// find the shortest distance
			// TODO: specifically distinguish the executed/non-executed branch,
			// currently we use branch distance to represent
			List<WalkPath> wps = new ArrayList<WalkPath>();
			try {
				wps = calculateBranchDistance(icfg, sm, br);
			} catch (Exception e) {
				// if unknown error happens, count as unreachable
				System.out.println("Caught exception: " + e);
			}
			// System.out.println("WalkPaths: " + wps);
			int shortestDistance = Integer.MAX_VALUE;
			for (WalkPath wp : wps) {
				int distance = WalkPath.calcDistance(wp);
				if (distance < shortestDistance)
					shortestDistance = distance;
			}
			// System.out.println("shortest distance: " + shortestDistance + " for
			// edgeId: " + edgeId);
			distancesMap.put(edgeId, shortestDistance);
		}

		// sort the distanceMap in reverse order
		Map<Integer, Integer> sortedMap = distancesMap.entrySet().stream()
				.sorted(Map.Entry.<Integer, Integer>comparingByValue().reversed())
				.filter(x -> x.getValue() != Integer.MAX_VALUE)
				.collect(java.util.stream.Collectors.toMap(Map.Entry::getKey,
						Map.Entry::getValue, (e1, e2) -> e1,
						java.util.LinkedHashMap::new));

		// write to the output file
		try {
			Files.write(Paths.get(rankedBranchFile), new GsonBuilder()
					.setPrettyPrinting().create().toJson(sortedMap).getBytes());
		} catch (IOException e) {
			e.printStackTrace();
		}
	}

	public static void analyze(String stuckBranchFile, String rankedBranchFile) {

		rankGivenBranches(stuckBranchFile, rankedBranchFile);

		// test code
		// TODO: perhaps can be used for a quick check? if cannot reach sanitizer hooked
		// funcs from beginning, then just random rank?
		// JimpleBasedInterproceduralCFG icfg = new JimpleBasedInterproceduralCFG(true);
		// List<Unit> ul = new ArrayList<Unit>();

		// for (SootClass sc : Scene.v().getClasses()) {
		// String fullSCName = sc.getName();
		// if (fullSCName.equals("java.lang.ProcessImpl")
		// || fullSCName.endsWith("." + "java.lang.ProcessImpl")) {
		// for (SootMethod _sm : sc.getMethods()) {
		// if (_sm.getName().equals("start")) {
		// System.out.println("find start method: "
		// + _sm.getSignature());
		// for (Unit ut : icfg.getStartPointsOf(_sm)) {
		// ul.add(ut);
		// }
		// }
		// }
		// }
		// }

		// System.out.println("start points of the goal function: " + ul);

		//// check is reachable or not
		// for (Unit ut : ul) {
		// System.out.println("ut " + ut + " is reachable: " + icfg.isReachable(ut));
		// }

		// CallGraph cg = Scene.v().getCallGraph();
		// for (SootMethod sm : entryPoints) {
		// Integer distance = calcFuncLevelDistance(cg, sm);
		// System.out.println("sm: " + sm + ", distance: " + distance);
		// }

	}

}
