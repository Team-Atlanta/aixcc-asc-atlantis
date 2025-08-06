package de.uzl.its.swat.utils;

public class InstructionCount {

  private static InstructionCount instance = null;
  private int count = 0x10000000;

  public static InstructionCount getInstance() {
    if (instance == null) {
      instance = new InstructionCount();
    }
    return instance;
  }

  public int getIncrementedCount() {
    count += 1;
    return count;
  }

}
