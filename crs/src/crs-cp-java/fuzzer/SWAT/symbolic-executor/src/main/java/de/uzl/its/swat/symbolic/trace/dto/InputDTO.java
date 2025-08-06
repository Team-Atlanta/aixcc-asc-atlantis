package de.uzl.its.swat.symbolic.trace.dto;

import java.util.ArrayList;

public class InputDTO {
    private String name;
    private Object value;
    private String type;
    private String lowerBound;
    private String upperBound;
    private ArrayList<String> hard_constraints;

    public InputDTO(String name, String value, String type, String lowerBound, String upperBound, ArrayList<String> hard_constraints) {
        this.name = name;
        this.value = value;
        this.type = type;
        this.lowerBound = lowerBound;
        this.upperBound = upperBound;
        this.hard_constraints = hard_constraints;
    }

    @Override
    public String toString() {
        return "InputDTO{"
                + "name='"
                + name
                + '\''
                + ", value="
                + value
                + ", type='"
                + type
                + '\''
                + ", lowerBound='"
                + lowerBound
                + '\''
                + ", upperBound='"
                + upperBound
                + '\''
                + '}';
    }

    /** Private default constructor for serialization */
    @SuppressWarnings("unused")
    private InputDTO() {}
}
