package de.uzl.its.swat.symbolic.invoke;

import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.CharValue;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.IntValue;
import de.uzl.its.swat.symbolic.value.reference.ObjectValue;
import de.uzl.its.swat.symbolic.value.reference.lang.CharacterObjectValue;
import de.uzl.its.swat.symbolic.value.reference.lang.StringValue;
import de.uzl.its.swat.symbolic.value.reference.array.ByteArrayValue;
import org.objectweb.asm.Type;
import java.nio.charset.Charset;

public class DigestUtilsInvocation {
    public static Value<?, ?> invokeMethod(
            String name,
            Value<?, ?>[] args,
            Type[] desc,
            SymbolicTraceHandler symbolicStateHandler) {
        return switch (name) {
            case "sha256" -> invokeSha256(args, desc, symbolicStateHandler);
            default -> PlaceHolder.instance;
        };
    }

    private static Value<?, ?> invokeSha256(Value<?, ?>[] args, Type[] desc, SymbolicTraceHandler sth) {
        if (args.length == 1) {
            System.out.println("### SHA256 ###");
            StringValue sv = args[0].asStringValue();
            IntValue sizeValue = new IntValue(sv.context, sv.concrete.length());
            ByteArrayValue bv = new ByteArrayValue(sv.context, sizeValue, ObjectValue.ADDRESS_UNKNOWN);
            bv.isFakeValue = true;
            bv.stringValue = sv;
            return bv;
            //return sv;
            /*
            byte[] concreteByteArray = s.concrete.getBytes(Charset.forName("UTF-8"));
            System.out.println("Concrete string: " + s.concrete);
            String a = "";
            for (int i=0; i<concreteByteArray.length; ++i) {
                a += concreteByteArray[i] + " ";
            }
            System.out.println("Concrete byteArray: " + a);
            return PlaceHolder.instance;
            */
            /*
            CharValue c = args[0].asCharValue();
            return new CharacterObjectValue(c.context, c, ObjectValue.ADDRESS_UNKNOWN);
            */
        } else {
            return PlaceHolder.instance;
        }
    }
}
