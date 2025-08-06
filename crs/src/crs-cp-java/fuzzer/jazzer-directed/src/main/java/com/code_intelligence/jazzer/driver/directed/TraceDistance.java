package com.code_intelligence.jazzer.driver.directed;

import sootup.callgraph.CallGraph;
import sootup.core.graph.BasicBlock;
import sootup.core.signatures.MethodSignature;
import sootup.java.core.JavaSootMethod;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class TraceDistance {
    private final CallGraph cg;
    private final List<MethodSignature> targets;
    private final FunctionDistance functionDistance;
    private final Map<JavaSootMethod, ArrayList<BasicBlock>> bbTrace;

    public TraceDistance(CallGraph cg, List<MethodSignature> targets, FunctionDistance functionDistance,
            Map<JavaSootMethod, ArrayList<BasicBlock>> bbTrace) {
        this.cg = cg;
        this.targets = targets;
        this.functionDistance = functionDistance;
        this.bbTrace = bbTrace;
    }

    public double calculate() {
        List<Double> distances = new ArrayList<>();
        for (JavaSootMethod javaSootMethod : bbTrace.keySet()) {
            BasicBlockDistance basicBlockDistance = new BasicBlockDistance(cg, targets, functionDistance,
                    javaSootMethod);
            for (BasicBlock bb : bbTrace.get(javaSootMethod)) {
                double bbDistance = basicBlockDistance.getBasicBlockDistance(bb);
                if (bbDistance == Double.POSITIVE_INFINITY) {
                    continue;
                }
                distances.add(bbDistance);
            }
        }

        // Return the average
        return distances.stream().mapToDouble(d -> d).average().orElse(Double.POSITIVE_INFINITY);
    }
}
