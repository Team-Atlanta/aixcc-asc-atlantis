package de.uzl.its.swat.symbolic.invoke;

import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.CharValue;
import de.uzl.its.swat.symbolic.value.reference.ObjectValue;
import de.uzl.its.swat.symbolic.value.reference.lang.CharacterObjectValue;
import de.uzl.its.swat.symbolic.value.reference.lang.StringValue;
import de.uzl.its.swat.symbolic.value.reference.array.ByteArrayValue;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.BooleanValue;

import org.sosy_lab.java_smt.api.*;
import org.sosy_lab.java_smt.api.NumeralFormula.IntegerFormula;
import org.sosy_lab.java_smt.api.SolverContext.ProverOptions;


import org.objectweb.asm.Type;

public class MessageDigestInvocation {

    public static Value<?, ?> invokeMethod(
            String name,
            Value<?, ?>[] args,
            Type[] desc,
            SymbolicTraceHandler symbolicStateHandler) {
        return switch (name) {
            case "isEqual" -> invokeIsEqual(args, desc, symbolicStateHandler);
            default -> PlaceHolder.instance;
        };
    }

    private static Value<?, ?> invokeIsEqual(Value<?, ?>[] args, Type[] desc, SymbolicTraceHandler sth) {
        if (args.length == 2) {
            ByteArrayValue bv0 = (ByteArrayValue) args[0];
            ByteArrayValue bv1 = (ByteArrayValue) args[1];
            if (bv0.isFakeValue && bv1.isFakeValue) {
                StringValue sv0 = bv0.stringValue;
                StringValue sv1 = bv1.stringValue;
                boolean concreteEquals = sv0.concrete.equals(sv1.concrete);
                FormulaManager fmgr = sv0.context.getFormulaManager();
                StringFormulaManager smgr = fmgr.getStringFormulaManager();
                BooleanFormula stringEqual = smgr.equal(sv0.formula, sv1.formula);
                return new BooleanValue(sv0.context, concreteEquals, stringEqual);
            }
            else {
                return PlaceHolder.instance;
            }
        } else {
            return PlaceHolder.instance;
        }
    }
}
