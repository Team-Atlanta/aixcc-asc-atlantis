package com.code_intelligence.jazzer.driver.directed;

import com.code_intelligence.jazzer.utils.Log;
import sootup.callgraph.CallGraph;
import sootup.core.signatures.MethodSignature;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class DistanceMap {
    private final CallGraph cg;
    private final Iterable<MethodSignature> targets;
    private final Map<MethodSignature, List<Integer>> distanceMap = new HashMap<>();

    public DistanceMap(CallGraph cg, Iterable<MethodSignature> targets) {
        this.cg = cg;
        this.targets = targets;

        // Log targets
        Log.info("Targets:");
        for (MethodSignature m : this.targets) {
            Log.info(m.getName());
        }

        initializeDistanceMap();
    }

    private void initializeDistanceMap() {
        for (MethodSignature m : this.cg.getMethodSignatures()) {
            this.distanceMap.put(m, new ArrayList<>());
        }

        for (MethodSignature target : this.targets) {
            // If target is not in the CG, it is not reachable. We can skip it.
            if (!cg.containsMethod(target)) {
                continue;
            }
            Map<MethodSignature, Integer> distances = calculateDistances(target);
            Log.info("Distances from " + target.getName() + ": " + distances);
            updateDistanceMap(distances);
        }
    }

    private Map<MethodSignature, Integer> calculateDistances(MethodSignature target) {
        Map<MethodSignature, Integer> distances = new HashMap<>();
        List<MethodSignature> currentMethods = new ArrayList<>();
        currentMethods.add(target);
        int distance = 0;
        while (!currentMethods.isEmpty()) {
            currentMethods = updateDistancesAndGetCurrentMethods(distances, currentMethods, distance);
            distance++;
        }
        return distances;
    }

    private List<MethodSignature> updateDistancesAndGetCurrentMethods(
            Map<MethodSignature, Integer> distances, List<MethodSignature> currentMethods, int distance) {
        List<MethodSignature> nextMethods = new ArrayList<>();
        for (MethodSignature m : currentMethods) {
            if (!distances.containsKey(m)) {
                distances.put(m, distance);
                nextMethods.addAll(this.cg.callsTo(m));
            } else if (distances.get(m) > distance) {
                distances.put(m, distance);
                nextMethods.addAll(this.cg.callsTo(m));
            }
        }
        return nextMethods;
    }

    private void updateDistanceMap(Map<MethodSignature, Integer> distances) {
        // Update the distance map
        for (MethodSignature m : this.cg.getMethodSignatures()) {
            if (distances.containsKey(m)) {
                this.distanceMap.get(m).add(distances.get(m));
            }
        }
    }

    public void printDistanceMap() {
        // Log the distance map
        System.out.println("Distance map:");
        for (Map.Entry<MethodSignature, List<Integer>> entry : this.distanceMap.entrySet()) {
            System.out.println(entry.getKey().getName() + ": " + entry.getValue());
        }
    }

    public List<Integer> getDistances(MethodSignature m) {
        return this.distanceMap.get(m);
    }
}
