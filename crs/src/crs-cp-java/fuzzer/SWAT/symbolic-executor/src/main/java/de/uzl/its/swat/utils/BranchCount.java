package de.uzl.its.swat.utils;

public class BranchCount {

  private static BranchCount instance = null;
  private int count = 33000000;

  public static BranchCount getInstance() {
    if (instance == null) {
      instance = new BranchCount();
    }
    return instance;
  }

  public int getIncrementedCount() {
    count += 1;
    return count;
  }

}
