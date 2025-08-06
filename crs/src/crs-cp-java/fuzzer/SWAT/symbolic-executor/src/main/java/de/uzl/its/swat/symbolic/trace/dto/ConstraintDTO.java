package de.uzl.its.swat.symbolic.trace.dto;

import java.util.ArrayList;

import de.uzl.its.swat.utils.*;

public class ConstraintDTO {
    @SuppressWarnings("unused")
    private ArrayList<BranchDTO> trace;

    @SuppressWarnings("unused")
    private ArrayList<InputDTO> inputs;

    @SuppressWarnings("unused")
    private ArrayList<SymbolicVariables> symbolicVariables;

    public ConstraintDTO(ArrayList<InputDTO> inputs, ArrayList<BranchDTO> trace) {
        this.trace = trace;
        this.inputs = inputs;
        this.symbolicVariables = SymbolicVariables.addedVariables;
    }

    @SuppressWarnings("unused")
    public ConstraintDTO() {}
}
