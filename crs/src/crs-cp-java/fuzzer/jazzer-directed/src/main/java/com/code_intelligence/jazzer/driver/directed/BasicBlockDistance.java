package com.code_intelligence.jazzer.driver.directed;

import sootup.callgraph.CallGraph;
import sootup.core.graph.BasicBlock;
import sootup.core.graph.StmtGraph;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.signatures.MethodSignature;
import sootup.java.core.JavaSootMethod;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class BasicBlockDistance {
    private static final double C = 10;
    private final CallGraph cg;
    private final Iterable<MethodSignature> targets;
    private final FunctionDistance fd;
    private final JavaSootMethod method;
    private final Map<BasicBlock, Double> basicBlockDistanceMap = new HashMap<>();

    BasicBlockDistance(CallGraph cg, Iterable<MethodSignature> targets, FunctionDistance functionDistance,
            JavaSootMethod method) {
        this.cg = cg;
        this.targets = targets;
        this.fd = functionDistance;
        this.method = method;

        initializeBasicBlockDistanceMap();
    }

    // Function to get an iterable of all basic blocks in the method
    private Iterable<BasicBlock> getBasicBlocks() {
        StmtGraph stmtGraph = this.method.getBody().getStmtGraph();
        return stmtGraph.getBlocks();
    }

    private double getMinimalFunctionDistance(BasicBlock bb) {
        double minDistance = Double.POSITIVE_INFINITY;
        for (Object obj : bb.getStmts()) {
            if (obj instanceof Stmt) {
                Stmt stmt = (Stmt) obj;
                if (!stmt.containsInvokeExpr()) {
                    continue;
                }
                MethodSignature target = stmt.getInvokeExpr().getMethodSignature();
                double functionDistance = this.fd.getFunctionDistance(target);
                if (functionDistance < minDistance) {
                    minDistance = functionDistance;
                }
            }
        }
        return minDistance;
    }

    // Function to set all basic blocks to a given distance
    private void setBasicBlockDistance(double distance) {
        for (BasicBlock bb : getBasicBlocks()) {
            this.basicBlockDistanceMap.put(bb, distance);
        }
    }

    private void initializeBasicBlockDistanceMap() {
        // First, if the function distance for this method is zero, all basic blocks have a distance of zero
        if (this.fd.getFunctionDistance(this.method.getSignature()) == 0) {
            setBasicBlockDistance(0);
        } else if (this.fd.getFunctionDistance(this.method.getSignature()) == Double.POSITIVE_INFINITY) {
            setBasicBlockDistance(Double.POSITIVE_INFINITY);
        } else {
            // First, go through all basic blocks that call a method with a finite distance
            for (BasicBlock bb : getBasicBlocks()) {
                double minDistance = getMinimalFunctionDistance(bb);
                if (minDistance != Double.POSITIVE_INFINITY) {
                    this.basicBlockDistanceMap.put(bb, minDistance * C);
                }
            }

            RawBlockDistance rawBlockDistance = new RawBlockDistance();
            //rawBlockDistance.printRawBlockDistanceMap();

            // Then, update all remaining basic blocks
            for (BasicBlock bb : getBasicBlocks()) {
                if (!this.basicBlockDistanceMap.containsKey(bb)) {
                    double distance = calculateBasicBlockDistance(bb, rawBlockDistance);
                    this.basicBlockDistanceMap.put(bb, distance);
                }
            }
        }
    }

    private double calculateBasicBlockDistance(BasicBlock bb, RawBlockDistance rawBlockDistance) {
        List<Double> distances = rawBlockDistance.getDistances(bb);
        double distance = 0;
        for (double d : distances) {
            distance += 1.0 / d;
        }
        return 1.0 / distance;
    }

    public double getBasicBlockDistance(BasicBlock bb) {
        return this.basicBlockDistanceMap.get(bb);
    }

    public void printBasicBlockDistanceMap() {
        System.out.println("Basic block distance map for " + this.method.getSignature() + ":");
        for (BasicBlock bb : this.basicBlockDistanceMap.keySet()) {
            System.out.println(bb.toString() + ": " + this.basicBlockDistanceMap.get(bb));
        }
    }

    private class RawBlockDistance {
        // This does the same as DistanceMap but for basic blocks
        private final Map<BasicBlock, List<Double>> distances = new HashMap<>();

        public RawBlockDistance() {
            initializeRawBlockDistance();
        }

        private void initializeRawBlockDistance() {
            for (BasicBlock bb : BasicBlockDistance.this.getBasicBlocks()) {
                this.distances.put(bb, new ArrayList<>());
            }

            for (BasicBlock bb : basicBlockDistanceMap.keySet()) {
                Map<BasicBlock, Double> distances = calculateRawBlockDistances(bb);
                updateRawBlockDistance(distances);
            }
        }

        private Map<BasicBlock, Double> calculateRawBlockDistances(BasicBlock bb) {
            Map<BasicBlock, Double> distances = new HashMap<>();
            List<BasicBlock> currentBlocks = new ArrayList<>();
            currentBlocks.add(bb);
            // We start with the function distance of this method as the distance
            double distance = basicBlockDistanceMap.get(bb);
            while (!currentBlocks.isEmpty()) {
                currentBlocks = updateRawBlockDistancesAndGetCurrentBlocks(distances, currentBlocks, distance);
                distance++;
            }
            return distances;
        }

        private List<BasicBlock> updateRawBlockDistancesAndGetCurrentBlocks(
                Map<BasicBlock, Double> distances, List<BasicBlock> currentBlocks, double distance) {
            List<BasicBlock> nextBlocks = new ArrayList<>();
            for (BasicBlock bb : currentBlocks) {
                if (!distances.containsKey(bb)) {
                    distances.put(bb, distance);
                    nextBlocks.addAll(bb.getPredecessors());
                } else if (distances.get(bb) > distance) {
                    distances.put(bb, distance);
                    nextBlocks.addAll(bb.getPredecessors());
                }
            }
            return nextBlocks;
        }

        private void updateRawBlockDistance(Map<BasicBlock, Double> distances) {
            // For every basic block, add the distance to the raw block distance map
            for (BasicBlock bb : BasicBlockDistance.this.getBasicBlocks()) {
                if (distances.containsKey(bb)) {
                    this.distances.get(bb).add(distances.get(bb));
                }
            }
        }

        private List<Double> getDistances(BasicBlock bb) {
            return this.distances.get(bb);
        }

        public void printRawBlockDistanceMap() {
            System.out.println("Raw block distance map:");
            for (BasicBlock bb : this.distances.keySet()) {
                System.out.println(bb.toString() + ": " + this.distances.get(bb));
            }
        }
    }
}
