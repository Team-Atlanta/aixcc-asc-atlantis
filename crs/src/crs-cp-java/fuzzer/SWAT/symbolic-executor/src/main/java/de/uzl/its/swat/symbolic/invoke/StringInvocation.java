package de.uzl.its.swat.symbolic.invoke;

import de.uzl.its.swat.config.*;
import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.*;
import de.uzl.its.swat.symbolic.value.reference.array.*;
import de.uzl.its.swat.symbolic.value.reference.lang.*;
import org.objectweb.asm.Type;

public class StringInvocation {

    public static Value<?, ?> invokeMethod(
            String name,
            Value<?, ?>[] args,
            Type[] desc,
            SymbolicTraceHandler symbolicTraceHandler) {
	    System.out.println("StringInvocation: invoked " + name);
        return switch (name) {
			case "<init>"  -> invokeInit(args, desc);
            case "valueOf" -> invokeValueOf(args, desc);
            default -> PlaceHolder.instance;
        };
    }

	private static Value<?, ?> invokeInit(Value<?, ?>[] args, Type[] desc) {
        /* possible constructors
        *
        // 0 args
        String()

        // 1 args
        String(byte[] bytes)
        String(char[] value)
        String(String original)
        String(StringBuffer buffer)
        String(StringBuilder builder)

        // 2 args
        String(byte[] bytes, String charsetName)
        String(byte[] bytes, Charset charset)

        // 3 args
        String(char[] value, int offset, int count)
        String(byte[] bytes, int offset, int length)
        String(int[] codePoints, int offset, int count)

        // 4 args
        String(byte[] bytes, int offset, int length, String charsetName)
        String(byte[] bytes, int offset, int length, Charset charset)
        */
    System.out.println("ARGS LENGTH: " + args.length);
	if (args.length == 0) {
		// new String() -- do nothing
        return PlaceHolder.instance;
	} else if (args.length == 1) {
        if (args[0].concrete == null) {
            // make a new symbolic string variable
            System.out.println("Create a new symvar");;
            StringValue ret = new StringValue(args[0].context, "", -1);
            ret.MAKE_SYMBOLIC(1);
            return ret;

        } else if (args[0] instanceof StringValue s) {
            // String(String original)
            /*
            System.out.println("Creating a string value from [" + s.concrete + "]");
			System.out.println("Formula: " + str.formula);
			System.out.println("Get address: " + str.getAddress());
            StringValue ret = new StringValue(str.context, str.concrete, str.formula, -1);
			System.out.println("Returning Formula: " + ret.formula);
            */
			return PlaceHolder.instance;
        }
        else {
            return PlaceHolder.instance;
        }
    } else if (args.length == 2) {
        return PlaceHolder.instance;
    } else if (args.length == 3) {
        return PlaceHolder.instance;
    } else if (args.length == 4) {
        return PlaceHolder.instance;
    }

		return PlaceHolder.instance;
	}

    private static Value<?, ?> invokeValueOf(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            return switch (desc[0].getDescriptor()) {
                case "I" -> args[0].asIntValue().asStringValue();
                case "F" -> args[0].asFloatValue().asStringValue();
                case "D" -> args[0].asDoubleValue().asStringValue();
                case "J" -> args[0].asLongValue().asStringValue();
                case "C" -> args[0].asCharValue().asStringValue();
                case "[C" -> args[0].asObjectValue()
                        .asArrayValue()
                        .asCharArrayValue()
                        .asStringValue();
                case "Z" -> args[0].asBooleanValue().asStringValue();
                default -> PlaceHolder.instance;
            };
        } else if (args.length == 3) {
            return invokeValueOf(
                    args[0].asObjectValue().asArrayValue().asCharArrayValue(),
                    args[1].asIntValue(),
                    args[2].asIntValue());
        } else {
            return PlaceHolder.instance;
        }
    }

    private static Value<?, ?> invokeValueOf(CharArrayValue data, IntValue offset, IntValue count) {
        return PlaceHolder.instance;
    }
}
