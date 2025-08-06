package com.code_intelligence.jazzer.driver.directed;

import sootup.callgraph.CallGraph;
import sootup.core.signatures.MethodSignature;

import java.util.HashMap;
import java.util.Map;

public class FunctionDistance {
    private final CallGraph cg;
    private final Iterable<MethodSignature> targets;
    private final DistanceMap distanceMap;
    private final Map<MethodSignature, Double> functionDistanceMap = new HashMap<>();

    public FunctionDistance(CallGraph cg, Iterable<MethodSignature> targets, DistanceMap distanceMap) {
        this.cg = cg;
        this.targets = targets;
        this.distanceMap = distanceMap;

        initializeFunctionDistanceMap();
    }

    private void initializeFunctionDistanceMap() {
        // The distance gets calculated as the harmonic mean of the distances
        for (MethodSignature m : this.cg.getMethodSignatures()) {
            double distance = calculateFunctionDistance(m);
            this.functionDistanceMap.put(m, distance);
        }
    }

    private double calculateFunctionDistance(MethodSignature m) {
        double distance = 0;
        for (int d : this.distanceMap.getDistances(m)) {
            distance += 1.0 / d;
        }
        return 1.0 / distance;
    }

    public double getFunctionDistance(MethodSignature m) {
        Double distance = this.functionDistanceMap.get(m);
        if (distance == null) {
            return Double.POSITIVE_INFINITY;
        }
        return distance;
    }

    public void printFunctionDistanceMap() {
        System.out.println("Function distance map:");
        for (MethodSignature m : this.functionDistanceMap.keySet()) {
            System.out.println(m.getName() + ": " + this.functionDistanceMap.get(m));
        }
    }
}
