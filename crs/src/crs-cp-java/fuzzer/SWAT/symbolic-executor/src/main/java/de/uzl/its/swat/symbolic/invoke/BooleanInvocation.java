package de.uzl.its.swat.symbolic.invoke;

import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.primitive.numeric.floatingpoint.*;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.*;
import de.uzl.its.swat.symbolic.value.reference.lang.*;

import de.uzl.its.swat.symbolic.value.reference.ObjectValue;
import de.uzl.its.swat.symbolic.value.reference.lang.CharacterObjectValue;
import org.objectweb.asm.Type;

import org.sosy_lab.java_smt.api.*;
import org.sosy_lab.java_smt.api.BooleanFormula;
import org.sosy_lab.java_smt.api.NumeralFormula.*;
import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.trace.InputElement;
import de.uzl.its.swat.symbolic.SymbolicTraceHandlerStore;
import java.util.ArrayList;
import java.util.Arrays;



public class BooleanInvocation {

    public static Value<?, ?> invokeMethod(
            String name,
            Value<?, ?>[] args,
            Type[] desc,
            SymbolicTraceHandler symbolicStateHandler) {
        return switch (name) {
            case "valueOf" -> invokeValueOf(args, desc, symbolicStateHandler);
            case "parseBoolean" -> invokeValueOf(args, desc, symbolicStateHandler);
            default -> PlaceHolder.instance;
        };
    }

    private static Value<?, ?> invokeValueOf(Value<?, ?>[] args, Type[] desc, SymbolicTraceHandler sth) {
        if (args.length == 1) {
            System.out.println("Classname: " + args[0].getClass().getName());
            if (args[0] instanceof BooleanValue) {
                BooleanValue b = args[0].asBooleanValue();
                return new BooleanObjectValue(b.context, b, ObjectValue.ADDRESS_UNKNOWN);
            }
            else if (args[0] instanceof StringValue) {
                StringValue sv = args[0].asStringValue();
                StringValue trueValue = new StringValue(sv.context, "true", ObjectValue.ADDRESS_UNKNOWN);
                StringValue TrueValue = new StringValue(sv.context, "True", ObjectValue.ADDRESS_UNKNOWN);
                StringValue falseValue = new StringValue(sv.context, "false", ObjectValue.ADDRESS_UNKNOWN);
                StringValue FalseValue = new StringValue(sv.context, "False", ObjectValue.ADDRESS_UNKNOWN);

                FormulaManager fmgr = sv.context.getFormulaManager();
                BooleanFormulaManager bmgr = fmgr.getBooleanFormulaManager();
                StringFormulaManager smgr = fmgr.getStringFormulaManager();


                BooleanFormula booleanString0 = smgr.equal(sv.formula, trueValue.formula);
                BooleanFormula booleanString1 = smgr.equal(sv.formula, TrueValue.formula);
                BooleanFormula booleanString2 = smgr.equal(sv.formula, falseValue.formula);
                BooleanFormula booleanString3 = smgr.equal(sv.formula, FalseValue.formula);

                BooleanFormula collectedStringFormula = bmgr.or(booleanString0, booleanString1);
                collectedStringFormula = bmgr.or(collectedStringFormula, booleanString2);
                collectedStringFormula = bmgr.or(collectedStringFormula, booleanString3);

                // add hard constraint
                InputElement ie = sth.getFirstInputElement();
                System.out.println("Input element: " + ie);
                ArrayList<String> hardConstraintsOnInput = ie.getHardConstraints();
                try {
                    hardConstraintsOnInput.add(fmgr.dumpFormula(fmgr.simplify(collectedStringFormula)).toString());
                } catch (Exception e) {
                    System.out.println(e.getMessage());
                    e.printStackTrace();
                }


                boolean concreteTrue = sv.concrete.equals("true") || sv.concrete.equals("True");

                BooleanFormula collectedTrueFormula = smgr.equal(trueValue.formula, sv.formula);
                collectedTrueFormula = bmgr.or(collectedTrueFormula, smgr.equal(TrueValue.formula, sv.formula));

                System.out.println("Collected True: " + collectedTrueFormula.toString());

                BooleanFormula collectedFalseFormula = smgr.equal(falseValue.formula, sv.formula);
                collectedFalseFormula = bmgr.or(collectedFalseFormula, smgr.equal(FalseValue.formula, sv.formula));
                collectedFalseFormula = bmgr.not(collectedFalseFormula);
                System.out.println("Collected False: " + collectedFalseFormula.toString());
                
                BooleanFormula collectedFormula = bmgr.and(collectedTrueFormula, collectedFalseFormula);

                BooleanValue b = new BooleanValue(sv.context, concreteTrue, collectedFormula);
                System.out.println("Returning Boolean value");
                return b;
                //return new BooleanObjectValue(sv.context, b, ObjectValue.ADDRESS_UNKNOWN);
            }
            return PlaceHolder.instance;
        } else {
            return PlaceHolder.instance;
        }
    }
}
