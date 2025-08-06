package de.uzl.its.swat.symbolic.value.reference.array;

import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.IntValue;
import de.uzl.its.swat.symbolic.value.reference.lang.StringValue;
import java.util.HashMap;
import org.sosy_lab.java_smt.api.*;

/**
 * Wrapper for Arrays that contain String values.
 *
 * @author Nils Loose
 * @version 2022.07.25
 */
public class StringArrayValue
        extends AbstractArrayValue<
                NumeralFormula.IntegerFormula, StringFormula, IntValue, StringValue, String[]> {

    public HashMap<Integer, Integer> addressMap = new HashMap<Integer, Integer>();
    public String[] concrete_val;
    private IntValue symbolicSize;

    public StringArrayValue(SolverContext context, IntValue size, int address) {
        super(context, FormulaType.IntegerType, FormulaType.StringType, size, address);
        this.symbolicSize = size;
        concrete_val = new String[size.concrete];
        initArray(size.concrete);
    }

    public StringArrayValue(
            SolverContext context,
            IntValue size,
            int address,
            IntValue parentRefIdx,
            ArrayArrayValue parentRef) {
        this(context, size, address);
        this.parentRefIdx = parentRefIdx;
        this.parentRef = parentRef;
    }

    public StringArrayValue(SolverContext context, String[] concrete, int address) {
        super(
                context,
                FormulaType.IntegerType,
                FormulaType.StringType,
                new IntValue(context, concrete.length),
                address);
        this.symbolicSize = new IntValue(context, concrete.length);
        this.concrete_val = concrete;

        initArray(concrete);
    }
    public StringValue getAt(int index) {
        try {
            return new StringValue(
                context,
                concrete_val[index],
                amgr.select(formula, getIndex(index)),
                addressMap.get(index));
        } catch (ArrayIndexOutOfBoundsException e) {
            // Optionally, handle the exception, e.g., return null or throw a more descriptive exception
            System.out.println("Index out of bounds: " + index);
            return null;
        }
    }

    public IntValue getLength() {
        return this.symbolicSize;
    }

    @Override
    StringFormula getDefaultValue() {
        return context.getFormulaManager().getStringFormulaManager().makeString("");
    }

    @Override
    NumeralFormula.IntegerFormula getIndex(int i) {
        return context.getFormulaManager().getIntegerFormulaManager().makeNumber(i);
    }

    @Override
    public StringValue getElement(IntValue idx) {
      try {
        // ToDo Can we get the actual address?
        //StringFormula sf = context.getFormulaManager().simplify(amgr.select(formula, idx.formula));
        StringFormula sf = amgr.select(formula, idx.formula);
        System.out.println("Retrieving from StringArray idx " + idx.concrete + " formula: " + idx.formula);
        System.out.println("String formula " + sf);
        System.out.println("Address " + addressMap.get(idx.concrete));
        return new StringValue(
                context,
                concrete_val[idx.concrete],
                sf,
                addressMap.get(idx.concrete));
      }
      catch (Exception e) {
        System.out.println(e.getMessage());
        e.printStackTrace();
        return null;
      }
    }

    public void storeElement(IntValue idx, StringValue val) {
        try {
            concrete_val[idx.concrete] = val.concrete;
            formula = amgr.store(formula, idx.formula, val.formula);
            addressMap.put(idx.concrete, val.getAddress());

            if (parentRef != null) {
                parentRef.updateFormula(parentRefIdx, formula);
            }

        } catch (ArrayIndexOutOfBoundsException e) {
            System.out.println("error on index out of bound");
        }
    }

    @Override
    protected void initArray(int size) {
        // ToDo (Nils): Is this needed or correct?
        // For Multinewarrays it seems needed as rthe values are else free i.e. arbitrary
        for (int i = 0; i < size; i++) {
            formula = amgr.store(formula, getIndex(i), getDefaultValue());
            concrete_val[i] = "";
            addressMap.put(i, 0);
        }
    }

    protected void initArray(String[] array) {
        StringFormulaManager smgr = context.getFormulaManager().getStringFormulaManager();
        // ToDo (Nils): Is this needed or correct?
        for (int i = 0; i < array.length; i++) {
            formula = amgr.store(formula, getIndex(i), smgr.makeString(concrete_val[i]));
        }
    }

    @Override
    public AbstractArrayValue<
                    NumeralFormula.IntegerFormula, StringFormula, IntValue, StringValue, String[]>
            asArrayValue() {
        return this;
    }

    /**
     * Returns the string representation of the value used to visualize the stack. The
     * representation is not complete.
     *
     * @return the string representation of the value.
     */
    @Override
    public String toString() {
        return genericToString("[Ljava/lang/String;");
    }
}
