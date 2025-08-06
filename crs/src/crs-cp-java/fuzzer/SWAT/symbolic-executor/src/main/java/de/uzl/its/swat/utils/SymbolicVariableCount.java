package de.uzl.its.swat.utils;

import java.util.ArrayList;

public class SymbolicVariableCount {

  private static SymbolicVariableCount instance = null;
  private int count;
  private ArrayList<String> variableList;

  public SymbolicVariableCount() {
      count = 0;
      variableList = new ArrayList<String>();
  }

  public static SymbolicVariableCount getInstance() {
    if (instance == null) {
      instance = new SymbolicVariableCount();
    }
    return instance;
  }

  public int getIncrementedCount() {
    count += 1;
    return count;
  }

  public void setNewVariable(String variableName) {
      variableList.add(variableName);
  }

}
