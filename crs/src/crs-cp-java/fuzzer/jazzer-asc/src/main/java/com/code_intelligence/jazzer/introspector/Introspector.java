package com.code_intelligence.jazzer.introspector;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.google.gson.GsonBuilder;
import com.code_intelligence.jazzer.introspector.Constants;
import com.code_intelligence.jazzer.runtime.CoverageMap;
import com.code_intelligence.jazzer.runtime.SanitizerData;
import com.code_intelligence.jazzer.runtime.SanitizerData.SanitizerInfo;

public class Introspector {

  /*
   * Switch button for self-introspection.
   */
  private static boolean selfIntrospection = false;
  private static String dumpFile = "";
  private static String dumpClassesDir = "";

  public static void setSelfIntrospection(String _dumpFile, String _dumpClassesDir) {
    dumpFile = _dumpFile;
    dumpClassesDir = _dumpClassesDir;
    selfIntrospection = (dumpFile.isEmpty() || dumpClassesDir.isEmpty()) ? false : true;
    if (selfIntrospection) {
      SanitizerData.enable();
    }
  }

  public static boolean enabled() {
    return selfIntrospection;
  }

  /*
   * Seed info of this execution.
   */
  public static byte[] curExecutionSeed = null;
  public static String seedSHA1 = null;

  private static String SHA1(byte[] data) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-1");
      md.update(data);
      byte[] digest = md.digest();

      StringBuilder hexString = new StringBuilder();

      for (byte b : digest) {
        hexString.append(String.format("%02x", b));
      }
      return hexString.toString();
    } catch (NoSuchAlgorithmException e) {
      e.printStackTrace();
      return "error-computing-sha1";
    }
  }

  private static void setCurExecutionSeed(byte[] seed) {
    curExecutionSeed = seed;
    seedSHA1 = SHA1(seed);
  }

  /*
   * Source information of the edge for introspection.
   */
  public static class SourceInfo {
    public String fileName;
    public String className;
    public Integer lineNo;

    public SourceInfo(String fileName, String className, Integer lineNo) {
      this.fileName = fileName;
      this.className = className;
      this.lineNo = lineNo;
    }
  }

  // TODO: collect this in somewhere appropriate
  private static Map<Integer, SourceInfo> edgeId2SourceInfo = new HashMap<>();

  /*
   * Main functions to record the sanitizer & cov info for introspection.
   */
  private static Map<String, Set<Integer>> seed2EdgeIds = new HashMap<>();
  private static Map<Integer, Set<String>> edgeId2Seeds = new HashMap<>();
  private static Map<String, Set<SanitizerInfo>> seed2SanitizerInfos = new HashMap<>();

  public static void preExecution(byte[] data) {
    if (!selfIntrospection)
      return;

    SanitizerData.clearSanitizerRecords();
    setCurExecutionSeed(data);
  }

  public static void postExecution() {
    if (!selfIntrospection)
      return;

    if (seedSHA1.equals(Constants.EMPTY_DATA_SHA1)) {
      return;
    }

    // record the coverage info
    Set<Integer> coveredIds = CoverageMap.getCoveredIds();
    seed2EdgeIds.put(seedSHA1, coveredIds);
    coveredIds.forEach(id -> {
      if (!edgeId2Seeds.containsKey(id)) {
        edgeId2Seeds.put(id, new HashSet<String>());
      }
      edgeId2Seeds.get(id).add(seedSHA1);
    });

    // record the sanitizer info
    seed2SanitizerInfos.put(seedSHA1, SanitizerData.getSanitizerInfos());

    // if (covDumpDir != "") {
    // // dump the coverage map for each executed input
    // Path dumpPath = Paths.get(covDumpDir, SHA1(data));
    // CoverageRecorder.dumpCoverageReport(dumpPath.toString(),
    // Arrays.stream(
    // CoverageMap.getCoveredIds().toArray(Integer[]::new)
    // ).mapToInt(Integer::intValue).toArray()
    // );
    // }
  }

  public static void dump() {
    if (!selfIntrospection)
      return;

    //System.err.println("[I] Dumping the introspection info to " + dumpClassesDir);
    
    SootSetup.setup(dumpClassesDir, List.of(dumpClassesDir), false);
    //System.err.println("[I] size of edgeId2Seeds: " + edgeId2Seeds.size());
    Map<Integer, Set<Integer>> execEdgeIdsOfStuckId = new HashMap<Integer, Set<Integer>>();
    Map<Integer, BranchSignature> stuckBranches = StuckBranchAnalyzer.getStuckBranches(edgeId2Seeds.keySet(), execEdgeIdsOfStuckId);
    //System.err.println("[I] size of stuckBranches: " + stuckBranches.size());

    // merge the introspection info
    Map<String, Object> introspection = new HashMap<>();
    introspection.put("seed2EdgeIds", seed2EdgeIds);
    introspection.put("seed2SanitizerInfos", seed2SanitizerInfos);
    introspection.put("stuckBranches", stuckBranches);
    introspection.put("execEdgeIdsOfStuckId", execEdgeIdsOfStuckId);
    // remove as this is duplicate info
    //introspection.put("edgeId2Seeds", edgeId2Seeds);
    introspection.put("allEdgeIds", new ArrayList<>(edgeId2Seeds.keySet()));

    // dump json to dumpFile
    try (FileWriter file = new FileWriter(dumpFile)) {
      file.write(new GsonBuilder().setPrettyPrinting().create().toJson(introspection));
      System.out.println("[I] Dumped the introspection info to " + dumpFile);
    } catch (IOException e) {
      e.printStackTrace();
    }

  }

}
