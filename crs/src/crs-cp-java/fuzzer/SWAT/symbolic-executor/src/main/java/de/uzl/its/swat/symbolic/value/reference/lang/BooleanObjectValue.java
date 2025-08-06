package de.uzl.its.swat.symbolic.value.reference.lang;

import com.google.common.base.Objects;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.*;
import de.uzl.its.swat.symbolic.value.reference.ObjectValue;
import org.objectweb.asm.Type;
import org.sosy_lab.java_smt.api.*;

public class BooleanObjectValue extends ObjectValue<Object, Object> {

    private BooleanValue booleanValue;
    private IntegerFormulaManager imgr;
    private StringFormulaManager smgr;

    public BooleanObjectValue(SolverContext context) {
        super(context, 100, -1);
        this.imgr = context.getFormulaManager().getIntegerFormulaManager();
        this.smgr = context.getFormulaManager().getStringFormulaManager();
        this.booleanValue = new BooleanValue(context, false);
    }

    public BooleanObjectValue(SolverContext context, BooleanValue booleanValue, int address) {
        super(context, 100, address);
        this.booleanValue = booleanValue;
        this.imgr = context.getFormulaManager().getIntegerFormulaManager();
        this.smgr = context.getFormulaManager().getStringFormulaManager();
    }

    /**
     * Gets the bound of the primitive type
     *
     * @param upper If the upper or lower bound should be created
     * @return The BooleanFormula that represents the bounds check
     */
    @Override
    public BooleanFormula getBounds(boolean upper) {
        if (booleanValue == null) {
            return context.getFormulaManager().getBooleanFormulaManager().makeBoolean(true);
        }
        return booleanValue.getBounds(upper);
    }

    public BooleanValue getBooleanValue() {
        return booleanValue;
    }

    @Override
    public Value<?, ?> invokeMethod(String name, Type[] desc, Value<?, ?>[] args) {
        return PlaceHolder.instance;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        if (!super.equals(o)) return false;
        BooleanObjectValue b = (BooleanObjectValue) o;
        return Objects.equal(booleanValue, b.booleanValue);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(booleanValue);
    }

    @Override
    public String toString() {
        return "Ljava/lang/Boolean; @" + Integer.toHexString(address);
    }
}
