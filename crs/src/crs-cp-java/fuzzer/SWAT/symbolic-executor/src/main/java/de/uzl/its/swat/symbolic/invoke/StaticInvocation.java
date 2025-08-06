package de.uzl.its.swat.symbolic.invoke;

import static de.uzl.its.swat.symbolic.value.reference.ObjectValue.ADDRESS_UNKNOWN;

import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.ValueFactory;
import de.uzl.its.swat.symbolic.value.primitive.numeric.floatingpoint.*;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.*;
import de.uzl.its.swat.symbolic.value.reference.lang.*;
import org.objectweb.asm.Type;
import org.sosy_lab.java_smt.api.*;
import org.sosy_lab.java_smt.api.BooleanFormula;
import org.sosy_lab.java_smt.api.NumeralFormula.*;

import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.trace.InputElement;
import de.uzl.its.swat.symbolic.SymbolicTraceHandlerStore;
import de.uzl.its.swat.utils.*;

import java.util.ArrayList;

public final class StaticInvocation {

    public static Value<?, ?> invokeMethod(
            String owner,
            String name,
            Type[] desc,
            Value<?, ?>[] args,
            SymbolicTraceHandler symbolicStateHandler) {
        System.out.println("Owner: " + owner);
        if (owner.equals("de/uzl/its/swat/Main")) {
            return InternalInvocation.invokeMethod(name, args, desc, symbolicStateHandler);
        } else if (owner.equals("java/lang/String")) {
            return StringInvocation.invokeMethod(name, args, desc, symbolicStateHandler);
        } else if (owner.equals("java/lang/Character")) {
            return CharacterInvocation.invokeMethod(name, args, desc, symbolicStateHandler);
        } else if (owner.equals("java/lang/Integer")) {
          return IntegerObjectValue.invokeStaticMethod(args[0].context, name, args, symbolicStateHandler);
        } else if (owner.equals("java/lang/Boolean")) {
          return BooleanInvocation.invokeMethod(name, args, desc, symbolicStateHandler);
        } else if (owner.equals("java/lang/Long")) {
          return IntegerObjectValue.invokeStaticMethod(args[0].context, name, args, symbolicStateHandler);
        }
        else if (owner.equals("java/lang/Double")) {
          return IntegerObjectValue.invokeStaticMethod(args[0].context, name, args, symbolicStateHandler);
        }
        else if (owner.equals("java/lang/Float")) {
          return IntegerObjectValue.invokeStaticMethod(args[0].context, name, args, symbolicStateHandler);
        }
        else if (owner.equals("java/lang/invoke/LambdaMetafactory")) {
            throw new RuntimeException("Unexpected case!");
        } else if (owner.equals("java/lang/Math") && name.equals("max") && args.length == 2) {
            if (args[0] instanceof IntValue a && args[1] instanceof IntValue b) {
                return invokeMax(a, b);
            }
            if (args[0] instanceof DoubleValue a && args[1] instanceof DoubleValue b) {
                return invokeMax(a, b);
            }
        } else if (owner.equals("java/lang/Math") && name.equals("min") && args.length == 2) {
            if (args[0] instanceof IntValue a && args[1] instanceof IntValue b) {
                return a.concrete < b.concrete ? a : b;
            }
        }
        else if (owner.equals("org/apache/commons/codec/digest/DigestUtils")) {
            return DigestUtilsInvocation.invokeMethod(name, args, desc, symbolicStateHandler);
        }
        else if (owner.equals("java/security/MessageDigest")) {
            return MessageDigestInvocation.invokeMethod(name, args, desc, symbolicStateHandler);
        }

        return PlaceHolder.instance;
    }

    private static IntValue invokeMax(IntValue a, IntValue b) {
        FormulaManager fmgr = a.context.getFormulaManager();
        BooleanFormula cond = fmgr.getIntegerFormulaManager().greaterOrEquals(a.formula, b.formula);
        NumeralFormula.IntegerFormula res =
                fmgr.getBooleanFormulaManager().ifThenElse(cond, a.formula, b.formula);
        return new IntValue(a.context, Math.max(a.concrete, b.concrete), res);
    }

    private static DoubleValue invokeMax(DoubleValue a, DoubleValue b) {
        FormulaManager fmgr = a.context.getFormulaManager();
        BooleanFormula cond =
                fmgr.getFloatingPointFormulaManager().greaterOrEquals(a.formula, b.formula);
        FloatingPointFormula res =
                fmgr.getBooleanFormulaManager().ifThenElse(cond, a.formula, b.formula);
        return new DoubleValue(a.context, Math.max(a.concrete, b.concrete), res);
    }
}
