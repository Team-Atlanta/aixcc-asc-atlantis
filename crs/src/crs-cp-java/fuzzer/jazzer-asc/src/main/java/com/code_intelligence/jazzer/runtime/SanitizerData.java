package com.code_intelligence.jazzer.runtime;

import java.util.Set;
import java.util.HashSet;

public class SanitizerData {

  /*
   * Sanitizer information collected during the execution for introspection. NOTE:
   * we do not track Integer Overflow currently to avoid huge usage of memory
   */
  public static class SanitizerInfo {
    public String sanitizerName;
    public String fullClassname;
    public String methodName;
    public String[] args;

    public SanitizerInfo(String sanitizerName, String fullClassname, String methodName, String[] args) {
      this.sanitizerName = sanitizerName;
      this.fullClassname = fullClassname;
      this.methodName = methodName;
      this.args = args;
    }
  }

  private static boolean selfIntrospection = false;

  private static Set<SanitizerInfo> sanitizerInfos = new HashSet<>();

  public static void enable() {
    selfIntrospection = true;
    System.out.println("Self-introspection for SanitizerData is enabled.");
  }

  public static void clearSanitizerRecords() {
    // new one instead of call .clear()
    sanitizerInfos = new HashSet<>();
  }

  public static Set<SanitizerInfo> getSanitizerInfos() {
    // get a copy set of sanitizerInfos
    return new HashSet<>(sanitizerInfos);
  }

  /*
   * This method is called via reflection sourcing from the hook code of sanitizer
   * methods.
   */
  public static void recordReachedSanitizer(String sanitizerName, String fullClassName, String methodName,
      String[] args) {
    if (!selfIntrospection)
      return;

    sanitizerInfos.add(new SanitizerInfo(sanitizerName, fullClassName, methodName, args));
  }

}
