package dictgen;

import soot.*;
import soot.jimple.Stmt;
import soot.jimple.StringConstant;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DictGen {
    public static int MAX_CG_DEPTH = 3;

    private static void traverseCallGraph(SootMethod sm, CallGraph cg, List<SootMethod> visited,
            int depth) {
        if (depth > MAX_CG_DEPTH)
            return;

        Iterator<Edge> iter = cg.edgesOutOf(sm);
        while (iter.hasNext()) {
            Edge e = iter.next();
            SootMethod tgt = e.tgt();
            String fullSCName = tgt.getDeclaringClass().getName();

            //System.out.println(fullSCName);
            //System.out.println(e.src() + " -> " + e.tgt());

            if (visited.contains(tgt))
                continue;

            // org.apache.logging.**:com.fasterxml.**:org.apache.commons.**
            if (fullSCName.startsWith("java.") || fullSCName.startsWith("javax.") || fullSCName.startsWith("sun.") || fullSCName.startsWith("com.sun.") || fullSCName.startsWith("org.apache.logging") || fullSCName.startsWith("com.fasterxml") || fullSCName.startsWith("org.apache.commons")) {
                // ignore java/javax packages
                //System.out.println("Ignore common package: " + fullSCName);
                continue;
            }

            //if ((!fullSCName.contains("jenkins")) && (!fullSCName.contains("Fuzz"))) {
            //    // TODO: is this suitable?
            //    System.out.println("Ignore non-jenkins package: " + fullSCName);
            //    continue;
            //}

            visited.add(tgt);
            traverseCallGraph(tgt, cg, visited, depth + 1);
        }
    }

    private static List<String> logFuncNames = Arrays.asList("info", "warn", "warning", "error",
            "debug", "log", "trace", "fatal", "severe", "println", "print", "printf",
            "printStackTrace", "printTo", "printToStderr", "printToStdout", "printToSyserr",
            "printToSysout", "printToWriter", "printToWriterErr", "printToWriterOut", "logging");

    private static boolean isFilteredFunc(Unit u) {
        Stmt st = (Stmt) u;
        if (!st.containsInvokeExpr())
            return false;

        String funcName = st.getInvokeExpr().getMethod().getName();
        SootClass sc = st.getInvokeExpr().getMethod().getDeclaringClass();
        String className = sc.getName();
        // System.out.println("funcName: " + funcName + " in class: " + className);

        // filter log functions
        if (logFuncNames.contains(funcName))
            return true;

        // filter throwable constructors
        if (funcName.equals("<init>") && (className.endsWith("Exception")))
            return true;
        if (funcName.equals("<init>") && (className.endsWith("Error")))
            return true;
        if (funcName.equals("<init>") && (className.endsWith("Throwable")))
            return true;

        return false;
    }

    private static Set<String> collectStringLiterals(SootMethod sm) {
        // System.out.println("Method: " + sm.getName() + " in class: " +
        // sm.getDeclaringClass().getName());

        // TODO: perhaps we should also collect the string literals in the class fields out of the
        // methods
        Set<String> stringLiterals = new HashSet<String>();

        try {
            Body bd = sm.retrieveActiveBody();

            // System.out.println("Body: " + bd.toString());

            for (Unit u : bd.getUnits()) {
                if (!(u instanceof Stmt))
                    continue;
                if (isFilteredFunc(u))
                    continue;
                // iterate getUseBoxes(), if it is a StringConstant, add it to the set
                for (ValueBox vb : u.getUseBoxes()) {
                    Value v = vb.getValue();
                    if (v instanceof StringConstant) {
                        // System.out.println("String constant: " + ((StringConstant) v).value + "
                        // in
                        // unit: " + u);
                        String str = ((StringConstant) v).value;
                        if ((str.length() >= 1) && (str.length() <= 20))
                            stringLiterals.add(str);
                    }
                }
            }
        } catch (Exception e) {
            System.out.println("Caught error: " + e);
        }

        return stringLiterals;
    }

    private static void dumpDict(Set<String> allLiterals, String outputDict) {
        // print the collected string literals: each line is a string literal in format str[idx] =
        // "literal, print as hex value if not ascii readable"

        // create a file called outputDict, write the string literals to the file
        // format: str_1="literal1", str_2="literal2", ...

        StringBuilder sb = new StringBuilder();
        int idx = 1;
        for (String s : allLiterals) {
            sb.append("str_");
            sb.append(idx);
            sb.append("=\"");
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                if (c == 92) {
                    // \ -> \\
                    sb.append("\\\\");
                } else if (c >= 32 && c <= 126) {
                    // printable ascii characters
                    sb.append(c);
                } else {
                    sb.append("\\x");
                    sb.append(String.format("%02x", (int) c));
                }
            }
            sb.append("\"\n");
            idx++;
        }
        sb.append("#\n");

        // write code to create the file
        File file = new File(outputDict);

        try {
            BufferedWriter writer = new BufferedWriter(new FileWriter(file));
            writer.write(sb.toString());
            writer.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static SootMethod findTargetMethod(String targetClass, String targetMethod) {
        for (SootClass sc : Scene.v().getClasses()) {
            String fullSCName = sc.getName();
            if (fullSCName.equals(targetClass) || fullSCName.endsWith("." + targetClass)) {
                for (SootMethod _sm : sc.getMethods()) {
                    if (_sm.getName().equals(targetMethod)) {
                        return _sm;
                    }
                }
            }
        }
        return null;
    }

    public static void generate(String targetClass, String targetMethod, String outputDict) {
        Set<String> allLiterals = new HashSet<String>();
        SootMethod sm = findTargetMethod(targetClass, targetMethod);
        if (sm != null) {
            CallGraph cg = Scene.v().getCallGraph();
            System.out.println("Call graph size: " + cg.size());

            // 1. start from sm, traverse the call graph and collected the methods
            List<SootMethod> visited = new ArrayList<SootMethod>();
            visited.add(sm);
            traverseCallGraph(sm, cg, visited, 0);

            System.out.println("visited size: " + visited.size());

            // 2. generate dicts by collecting the string literals inside the methods
            for (SootMethod _sm : visited)
                allLiterals.addAll(collectStringLiterals(_sm));

        } else {
            System.out.println("No target method found: " + targetMethod + " in class: " + targetClass);
        }

        dumpDict(allLiterals, outputDict);
    }

}
