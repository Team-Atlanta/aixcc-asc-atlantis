package de.uzl.its.swat.utils;

import java.util.*;

public class SymbolicVariables {

    public static int variableCount = 0;
    public static ArrayList<SymbolicVariables> addedVariables = new ArrayList<SymbolicVariables>();

    public static void addNewSymbolicVariable(String name, String type) {
        SymbolicVariables sv = new SymbolicVariables(name, type);
        sv.variableIndex = ++SymbolicVariables.variableCount;
        System.out.println("Adding new symbolic variable: " + sv);
        addedVariables.add(sv);
    }

    public String variableName;
    public String variableType;
    public int variableIndex;
    
    public SymbolicVariables(String name, String type) {
        this.variableName = name;
        this.variableType = type;
        this.variableIndex = -1;
    }

    public String toString() {
        return "SymbolicVariable: " + variableName + " type: " + variableType + " idx: " + variableIndex;
    }
}
