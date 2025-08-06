package de.uzl.its.swat.symbolic.invoke;

import de.uzl.its.swat.config.*;
import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.*;
import de.uzl.its.swat.symbolic.value.reference.array.*;
import de.uzl.its.swat.symbolic.value.reference.lang.*;
import de.uzl.its.swat.utils.*;
import org.objectweb.asm.Type;

import org.sosy_lab.java_smt.api.*;
import org.sosy_lab.java_smt.api.NumeralFormula.IntegerFormula;
import de.uzl.its.swat.symbolic.trace.InputElement;

import java.util.*;

public class ConcolicProviderInvocation {

	private static Value<?, ?> invokeGetInt(Value<?, ?>[] args, Type[] desc, SymbolicTraceHandler symbolicTraceHandler) {
        // create a new symbolic integer
        System.out.println("Context: " + args[0].context + "@" + args[0].context.hashCode());
        IntValue iv = new IntValue(args[0].context, 0);
        int number = SymbolicVariableCount.getInstance().getIncrementedCount();
        String symbolicName = iv.MAKE_SYMBOLIC(number);
        symbolicTraceHandler.addInput(symbolicName, iv);
        SymbolicVariableCount.getInstance().setNewVariable(symbolicName);
        SymbolicVariables.addNewSymbolicVariable(symbolicName, "int");
        System.out.println("Number: " + number + " Formula: " + iv.formula.toString());
		return iv;
	}
	private static Value<?, ?> invokeGetString(Value<?, ?>[] args, Type[] desc, SymbolicTraceHandler symbolicTraceHandler) {
        // create a new symbolic string
        System.out.println("Context: " + args[0].context + "@" + args[0].context.hashCode());
        StringValue sv = new StringValue(args[0].context, "", -1);
        int number = SymbolicVariableCount.getInstance().getIncrementedCount();
        String symbolicName = sv.MAKE_SYMBOLIC(number);
        symbolicTraceHandler.addInput(symbolicName, sv);
        SymbolicVariableCount.getInstance().setNewVariable(symbolicName);
        SymbolicVariables.addNewSymbolicVariable(symbolicName, "String");
        // add constraint
        FormulaManager fmgr = args[0].context.getFormulaManager();
        StringFormulaManager smgr = fmgr.getStringFormulaManager();
        IntegerFormulaManager imgr = fmgr.getIntegerFormulaManager();
        BooleanFormulaManager bmgr = fmgr.getBooleanFormulaManager();
        IntegerFormula stringLengthFormula = smgr.length(sv.formula);
        BooleanFormula stringLengthGTEZero = imgr.greaterOrEquals(stringLengthFormula, imgr.makeNumber(0));
        BooleanFormula stringLengthGTEOne = imgr.greaterOrEquals(stringLengthFormula, imgr.makeNumber(1));
        
        StringValue nullStringValue = new StringValue(args[0].context, "\0", StringValue.ADDRESS_UNKNOWN);
        StringFormula firstCharacter = smgr.charAt(sv.formula, imgr.makeNumber(0));
        BooleanFormula firstNotNull = bmgr.and(bmgr.not(smgr.equal(firstCharacter, nullStringValue.formula)), stringLengthGTEOne);
        IntegerFormula lastIndex = imgr.subtract(stringLengthFormula, imgr.makeNumber(1));
        BooleanFormula lastGTEZero = imgr.greaterOrEquals(lastIndex, imgr.makeNumber(0));
        StringFormula lastString = smgr.charAt(sv.formula, lastIndex);
        BooleanFormula lastNotNull = bmgr.and(bmgr.not(smgr.equal(lastString, nullStringValue.formula)), lastGTEZero);
        
        //BooleanFormula combined = bmgr.and(firstNotNull, lastNotNull);
        BooleanFormula combined = firstNotNull;
        combined = bmgr.or(stringLengthGTEZero, combined);
        
        /*
        System.out.println("Null String formula: " + nullStringValue.formula);
        BooleanFormula doesNotContainNull = bmgr.not(smgr.contains(sv.formula, nullStringValue.formula));
        BooleanFormula combined = bmgr.and(doesNotContainNull, stringLengthGTEZero);
        */

        InputElement ie = symbolicTraceHandler.getFirstInputElement();
        ArrayList<String> hardConstraintsOnInput = ie.getHardConstraints();
        try {
            //hardConstraintsOnInput.add(fmgr.dumpFormula(fmgr.simplify(stringLengthGTEZero)).toString());
            hardConstraintsOnInput.add(fmgr.dumpFormula(fmgr.simplify(combined)).toString());
            //System.out.println("Hard: " + fmgr.dumpFormula(fmgr.simplify(combined)).toString());
        } catch (Exception e) {
            System.out.println(e.getMessage());
            e.printStackTrace();
        }
        System.out.println("Number: " + number + " Formula: " + sv.formula.toString());
		return sv;
	}


    public static Value<?, ?> invokeMethod(
            String name,
            Value<?, ?>[] args,
            Type[] desc,
            SymbolicTraceHandler symbolicTraceHandler) {
	    System.out.println("ConcolicProviderInvocation: invoked " + name);
        return switch (name) {
            case "getInt" -> invokeGetInt(args, desc, symbolicTraceHandler);
            case "consumeInt" -> invokeGetInt(args, desc, symbolicTraceHandler);
            case "getString" -> invokeGetString(args, desc, symbolicTraceHandler);
            case "consumeString" -> invokeGetString(args, desc, symbolicTraceHandler);
            default -> PlaceHolder.instance;
        };
    }
}
