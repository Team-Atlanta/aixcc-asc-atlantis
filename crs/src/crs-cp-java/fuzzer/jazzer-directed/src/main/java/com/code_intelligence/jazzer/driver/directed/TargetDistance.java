package com.code_intelligence.jazzer.driver.directed;

import com.code_intelligence.jazzer.driver.Opt;
import com.code_intelligence.jazzer.instrumentor.CoverageRecorder;
import com.code_intelligence.jazzer.instrumentor.InstrumentProbeInfo;
import com.code_intelligence.jazzer.utils.Log;
import sootup.callgraph.CallGraph;
import sootup.callgraph.CallGraphAlgorithm;
import sootup.callgraph.RapidTypeAnalysisAlgorithm;
import sootup.core.graph.BasicBlock;
import sootup.core.graph.StmtGraph;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.jimple.basic.Immediate;
import sootup.core.jimple.common.constant.IntConstant;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.signatures.MethodSignature;
import sootup.core.signatures.MethodSubSignature;
import sootup.core.types.Type;
import sootup.java.bytecode.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.JavaIdentifierFactory;
import sootup.java.core.JavaSootMethod;
import sootup.java.core.types.JavaClassType;
import sootup.java.core.views.JavaView;

import java.util.*;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import com.code_intelligence.jazzer.driver.directed.Util;

public class TargetDistance {
    private final int[] featureIDs;
    private final boolean useCounters;
    private static JavaView view;
    private static List<MethodSignature> targets;
    private static boolean inited = false;

    private static Set<MethodSignature> allCgEntries = new HashSet<>();
    private static CallGraph cg;
    private static FunctionDistance functionDistance;

    public TargetDistance(int[] featureIDs, boolean useCounters) {
        this.featureIDs = featureIDs;
        this.useCounters = useCounters;

        if (!inited) {
            String inputLocationDir = Opt.dumpClassesDir.get();
            AnalysisInputLocation inputLocation = new JavaClassPathAnalysisInputLocation(inputLocationDir);

            view = new JavaView(inputLocation);

            targets = getTargetMethods();
            inited = true;
        }
    }

    public synchronized double calculate() {
        if (targets.isEmpty()) {
            Log.error("No target methods found for directed fuzzing.");
            return -1;
        }

        // Get the call graph entries and all targeted methods
        Set<MethodSignature> cgEntries = getExecutedMethods();

        if (cgEntries.isEmpty()) {
            Log.info("No CG entry methods found for directed fuzzing.");
            return -1;
        }

        int count = allCgEntries.size();
        allCgEntries.addAll(cgEntries);
        if (count != allCgEntries.size()) {
            Log.info("New entries found");

            // Entries have changed, update the CG
            CallGraphAlgorithm rtaCG = new RapidTypeAnalysisAlgorithm(view);
            cg = rtaCG.initialize(new ArrayList<>(cgEntries));
            if (cg.getMethodSignatures().isEmpty()) {
                return -1;
            }

            //Log.info(cg.toString());
            Log.info("New call graph size: " + cg.getMethodSignatures().size());

            // Create a new distance map from the cg and the targets
            DistanceMap distanceMap = new DistanceMap(cg, targets);
            //distanceMap.printDistanceMap();

            functionDistance = new FunctionDistance(cg, targets, distanceMap);
            //System.out.println();
            //functionDistance.printFunctionDistanceMap();
        }

        Map<JavaSootMethod, ArrayList<BasicBlock>> bbTrace = getBasicBlockTrace();
        if (bbTrace.isEmpty()) {
            // This is a big problem, now we don't have any trace at all.
            Log.error("Unable to find any basic block for the trace.");
        }

        TraceDistance traceDistance = new TraceDistance(cg, targets, functionDistance, bbTrace);
        double score = traceDistance.calculate();
        return score;
    }

    private Set<MethodSignature> getExecutedMethods() {
        // Goes through the trace and returns the list of all executed methods (based on the probeId mapping)
        Set<MethodSignature> methods = new HashSet<>();

        for (int probeId : getProbeIDs()) {
            InstrumentProbeInfo probeInfo = CoverageRecorder.INSTANCE.getProbeMethodMapping().get(probeId);
            Optional<MethodSignature> oms = getMethodSignatureForProbeInfo(probeInfo);
            if (!oms.isPresent()) {
                continue;
            }
            MethodSignature methodSignature = oms.get();

            methods.add(methodSignature);
        }

        return methods;
    }

    private static MethodSignature generateMethodSignature(
            String className, String methodName, String returnType, List<Type> parameterTypes) {
        JavaClassType classType = JavaIdentifierFactory.getInstance().getClassType(className);
        Type returnTypeObj = JavaIdentifierFactory.getInstance().getType(returnType);
        MethodSubSignature methodSubSignature =
            JavaIdentifierFactory.getInstance().getMethodSubSignature(methodName, returnTypeObj, parameterTypes);

        return view.getIdentifierFactory().getMethodSignature(classType, methodSubSignature);
    }

    private Optional<MethodSignature> getMethodSignatureForProbeInfo(InstrumentProbeInfo probeInfo) {
        if (probeInfo == null) {
            return Optional.empty();
        }
        org.objectweb.asm.Type methodType = org.objectweb.asm.Type.getMethodType(probeInfo.getMethodSignature());

        String returnTypeStr = methodType.getReturnType().getClassName();

        List<Type> parameterTypes = new ArrayList<>();
        for (org.objectweb.asm.Type argumentType : methodType.getArgumentTypes()) {
            String argType = argumentType.getClassName();
            parameterTypes.add(JavaIdentifierFactory.getInstance().getType(argType));
        }

        return Optional.of(generateMethodSignature(probeInfo.getClassName(), probeInfo.getMethodName(), returnTypeStr,
            parameterTypes));
    }

    // Helper class for holding the regex and group order
    private static class PatternInfo {
        Pattern pattern;
        int[] groupOrder;

        PatternInfo(String regex, int... groupOrder) {
            this.pattern = Pattern.compile(regex);
            this.groupOrder = groupOrder;
        }
    }

    private static final List<PatternInfo> patterns = Arrays.asList(
            new PatternInfo("([\\w\\[\\]]+)\\s+([\\w\\.\\$]+)\\.([\\w]+)\\(([^\\)]*)\\)", 1, 2, 3, 4),
            new PatternInfo("([\\w\\.\\$]+)\\.([\\w]+):([\\w\\.]+)\\(([^\\)]*)\\)", 3, 1, 2, 4)
    );

    private static Optional<MethodSignature> getMethodSignatureForString(String s) {
        for (PatternInfo patternInfo : patterns) {
            Matcher matcher = patternInfo.pattern.matcher(s);

            if (matcher.find()) {
                String returnType = Util.guessFullClassName(matcher.group(patternInfo.groupOrder[0]));
                String className = matcher.group(patternInfo.groupOrder[1]);
                String methodName = matcher.group(patternInfo.groupOrder[2]);
                String[] argStrings = matcher.group(patternInfo.groupOrder[3]).split("\\s*,\\s*");

                List<Type> argTypes = Arrays.stream(argStrings)
                        .map(Util::guessFullClassName)
                        .map(JavaIdentifierFactory.getInstance()::getType)
                        .collect(Collectors.toList());

                return Optional.of(generateMethodSignature(className, methodName, returnType, argTypes));
            }
        }

        Log.warn("Invalid target format: " + s);
        return Optional.empty();
    }

    private static List<MethodSignature> getTargetMethods() {
        // Here, we go through the trace and return the list of all executed methods
        List<MethodSignature> l = new ArrayList<>();

        // Open the file and read one target from each line
        String targetsFilePath = Opt.directedFuzzingTargets.get();
        try {
            Scanner scanner = new Scanner(new java.io.File(targetsFilePath));
            while (scanner.hasNextLine()) {
                String target = scanner.nextLine();
                try {
                    Optional<MethodSignature> methodSignature = getMethodSignatureForString(target);
                    if (methodSignature.isPresent()) {
                        l.add(methodSignature.get());
                    } else {
                        Log.warn("Unable to get method signature for target: " + target);
                    }
                } catch (Exception e) {
                    Log.warn("Unable to get method signature for target: " + target + " - " + e);
                }
            }
            scanner.close();
        } catch (java.io.FileNotFoundException e) {
            Log.error("Targets file for directed fuzzing does not exist.");
        }

        return l;
    }

    private Map<JavaSootMethod, ArrayList<BasicBlock>> getBasicBlockTrace() {
        HashMap<JavaSootMethod, ArrayList<BasicBlock>> result = new HashMap<>();

        for (int probeId : getProbeIDs()) {
            boolean found = false;

            // Now, go through all the possible basic blocks in the view to find the one with the matching ID
            InstrumentProbeInfo probeInfo = CoverageRecorder.INSTANCE.getProbeMethodMapping().get(probeId);
            Optional<MethodSignature> oms = getMethodSignatureForProbeInfo(probeInfo);
            if (!oms.isPresent()) {
                continue;
            }
            MethodSignature methodSignature = oms.get();
            Optional<JavaSootMethod> m = view.getMethod(methodSignature);
            if (!m.isPresent()) {
                //Log.warn("Unable to find soot method for probeId " + probeId + ": " + methodSignature);
                continue;
            }
            JavaSootMethod javaSootMethod = m.get();

            StmtGraph stmtGraph = javaSootMethod.getBody().getStmtGraph();
            Iterable<BasicBlock> blocks = stmtGraph.getBlocks();
            for (BasicBlock bb : blocks) {
                Iterable<Stmt> stmts = bb.getStmts();
                for (Stmt stmt : stmts) {
                    // Check if this is a static invoke to recordCoverage
                    if (!stmt.containsInvokeExpr()) {
                        continue;
                    }
                    MethodSignature target = stmt.getInvokeExpr().getMethodSignature();
                    String classname = target.getDeclClassType().toString();
                    String mname = target.getName();
                    if (mname.equals("recordCoverage") &&
                            classname.equals("com.code_intelligence.jazzer.runtime.CoverageMap")) {
                        // Get the argument
                        Immediate i = stmt.getInvokeExpr().getArg(0);
                        IntConstant intConstant = (IntConstant) i;

                        if (intConstant.getValue() == probeId) {
                            if (!result.containsKey(javaSootMethod)) {
                                result.put(javaSootMethod, new ArrayList<>());
                            }
                            result.get(javaSootMethod).add(bb);
                            found = true;
                            break;
                        }
                    }
                }

                if (found) break;
            }

            if (!found) {
                // This is a problem. We didn't find the traced basic block ...
                Log.warn("Unable to find basic block for probeId " + probeId + ": " + methodSignature);
            }
        }

        return result;
    }

    private int[] getProbeIDs() {
        int[] resultArray = new int[featureIDs.length];
        for (int i = 0; i < featureIDs.length; i++) {
            resultArray[i] = featureIDs[i] / (useCounters ? 8 : 1);
        }

        return resultArray;
    }
}
