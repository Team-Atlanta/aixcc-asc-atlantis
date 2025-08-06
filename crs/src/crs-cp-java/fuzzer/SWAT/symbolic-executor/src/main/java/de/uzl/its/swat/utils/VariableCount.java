package de.uzl.its.swat.utils;

public class VariableCount {

  private static VariableCount instance = null;
  private int count = 10000000;

  public static VariableCount getInstance() {
    if (instance == null) {
      instance = new VariableCount();
    }
    return instance;
  }

  public int getIncrementedCount() {
    count += 1;
    return count;
  }

}
