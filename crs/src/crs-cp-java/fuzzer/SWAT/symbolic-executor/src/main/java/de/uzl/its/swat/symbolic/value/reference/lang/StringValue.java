package de.uzl.its.swat.symbolic.value.reference.lang;

import de.uzl.its.swat.config.Config;
import de.uzl.its.swat.symbolic.value.PlaceHolder;
import de.uzl.its.swat.symbolic.value.Value;
import de.uzl.its.swat.symbolic.value.VoidValue;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.BooleanValue;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.CharValue;
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.IntValue;
import de.uzl.its.swat.symbolic.value.reference.ObjectValue;
import de.uzl.its.swat.symbolic.value.reference.array.CharArrayValue;
import de.uzl.its.swat.symbolic.value.reference.array.StringArrayValue;

import java.io.UTFDataFormatException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.regex.PatternSyntaxException;

import org.objectweb.asm.Type;
import org.sosy_lab.java_smt.api.*;
import org.sosy_lab.java_smt.api.NumeralFormula.IntegerFormula;
import org.sosy_lab.java_smt.api.SolverContext.ProverOptions;

import java.lang.Thread;
import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import de.uzl.its.swat.symbolic.trace.InputElement;
import de.uzl.its.swat.symbolic.SymbolicTraceHandlerStore;

import de.uzl.its.swat.utils.*;

public class StringValue extends ObjectValue<StringFormula, String> {
    private static final String symbolicPrefix = "Ljava/lang/String";

    static final int REPLACE_COUNT = 10;
    private StringFormulaManager smgr;
    public Object[] symbolicStateArray;

    public StringValue(SolverContext context, String concrete, int address) {
        super(context, 100, address);
        this.smgr = context.getFormulaManager().getStringFormulaManager();
        this.concrete = concrete;
        this.formula = smgr.makeString(concrete);
    }

    public StringValue(SolverContext context, String concrete, StringFormula formula, int address) {
        super(context, 100, address);
        this.smgr = context.getFormulaManager().getStringFormulaManager();
        this.concrete = concrete;
        this.formula = formula;
    }

    //implementation borrowed from dalvik https://github.com/pxb1988/dalvik/blob/2bf1bcc652cd346d47a8778429de942c5d697ba3/dx/src/com/android/dx/util/Mutf8.java#L65
    public long getModifiedUtf8Length(String input,  boolean shortLength) throws UTFDataFormatException  {
        long result = 0;
        final int length = input.length();
        for (int i = 0; i < length; ++i) {
            char ch = input.charAt(i);
            if (ch != 0 && ch <= 127) { // U+0000 uses two bytes.
                ++result;
            } else if (ch <= 2047) {
                result += 2;
            } else {
                result += 3;
            }
            if (shortLength && result > 65535) {
                throw new UTFDataFormatException("String more than 65535 UTF bytes long");
            }
        }
        return result;
    }

    /**
     * Compares if two references are not identical
     *
     * @param o2 The other string
     * @return A BooleanFormula representing the result
     */
    @Override
    public BooleanFormula IF_ACMPNE(ObjectValue o2) {
        if (o2 instanceof StringValue s2) {
            BooleanFormulaManager bmgr = context.getFormulaManager().getBooleanFormulaManager();
            BooleanFormula b = bmgr.not(smgr.equal(formula, s2.formula));
            return b;
        } else {
            return super.IF_ACMPNE(o2);
        }
    }
    /**
     * Compares if two references are identical
     *
     * @param o2 The other string
     * @return A BooleanFormula representing the result
     */
    @Override
    public BooleanFormula IF_ACMPEQ(ObjectValue o2) {
        if (o2 instanceof StringValue s2) {
            BooleanFormula b = smgr.equal(formula, s2.formula);
            return b;
        } else {
            return super.IF_ACMPEQ(o2);
        }
    }

    @Override
    public Object getConcrete() {
        return concrete;
    }

    public String MAKE_SYMBOLIC(String namePrefix) {
        initSymbolic(namePrefix);
        formula = smgr.makeVariable(name);
        return name;
    }

    public String MAKE_SYMBOLIC() {
        initSymbolic(symbolicPrefix);
        formula = smgr.makeVariable(name);
        return name;
    }
    /**
     * Turns this IntValue into a symbolic variable
     *
     * @param idx
     * @return The numerical identifier of this symbolic variable
     */
    @Override
    public String MAKE_SYMBOLIC(long idx) {
        initSymbolic(symbolicPrefix, idx);
        formula = smgr.makeVariable(name);
        return name;
    }

    /**
     * Creates a formula that asserts that this symbolic value is withing the bounds of this type
     *
     * @param upper If the upper or lower bound should be created
     * @return The BooleanFormula that represents the bounds check
     */
    @Override
    public BooleanFormula getBounds(boolean upper) {
        return context.getFormulaManager().getBooleanFormulaManager().makeBoolean(true);
    }

    /**
     * Handles method invocation for Java's <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html">String</a>
     * (Java 16).
     *
     * @param name The name of the method that is called
     * @param desc The Type descriptions for all Arguments
     * @param args The Value's representing the arguments
     * @return The return Value of the Method, or a PlaceHolder::instance if the Method is not
     *     implemented or void should be returned
     */
    @Override
    public Value<?, ?> invokeMethod(String name, Type[] desc, Value<?, ?>[] args) {
	System.out.println("YJ invokeMethod for StringValue:" + name);
        return switch (name) {
            case "<init>" -> invokeInit(args, desc);
            case "charAt" -> invokeCharAt(args, desc);
            case "chars" -> invokeChars(args, desc);
            case "codePointAt" -> invokeCodePointAt(args, desc);
            case "codePointBefore" -> invokeCodePointBefore(args, desc);
            case "codePointCount" -> invokeCodePointCount(args, desc);
            case "codePoints" -> invokeCodePoints(args, desc);
            case "compareTo" -> invokeCompareTo(args, desc);
            case "compareToIgnoreCase" -> invokeCompareToIgnoreCase(args, desc);
            case "concat" -> invokeConcat(args, desc);
            case "contains" -> invokeContains(args, desc);
            case "contentEquals" -> invokeContentEquals(args, desc);
            case "describeConstable" -> invokeDescribeConstable(args, desc);
            case "endsWith" -> invokeEndsWith(args, desc);
            case "equals" -> invokeEquals(args, desc);
            case "equalsIgnoreCase" -> invokeEqualsIgnoreCase(args, desc);
            case "formatted" -> invokeFormatted(args, desc);
            case "getBytes" -> invokeGetBytes(args, desc);
            case "getChars" -> invokeGetChars(args, desc);
            case "hashCode" -> invokeHashCode(args, desc);
            case "indent" -> invokeIndent(args, desc);
            case "indexOf" -> invokeIndexOf(args, desc);
            case "intern" -> invokeIntern(args, desc);
            case "isBlank" -> invokeIsBlank(args, desc);
            case "isEmpty" -> invokeIsEmpty(args, desc);
            case "lastIndexOf" -> invokeLastIndexOf(args, desc);
            case "length" -> invokeLength(args, desc);
            case "lines" -> invokeLines(args, desc);
            case "matches" -> invokeMatches(args, desc);
            case "offsetByCodePoints" -> invokeOffsetByCodePoints(args, desc);
            case "regionMatches" -> invokeRegionMatches(args, desc);
            case "repeat" -> invokeRepeat(args, desc);
            case "replace" -> invokeReplace(args, desc);
            case "replaceAll" -> invokeReplaceAll(args, desc);
            case "replaceFirst" -> invokeReplaceFirst(args, desc);
            case "resolveConstantDesc" -> invokeResolveConstantDesc(args, desc);
            case "split" -> invokeSplit(args, desc);
            case "startsWith" -> invokeStartsWith(args, desc);
            case "strip" -> invokeStrip(args, desc);
            case "stripIndent" -> invokeStripIndent(args, desc);
            case "stripLeading" -> invokeStripLeading(args, desc);
            case "stripTrailing" -> invokeStripTrailing(args, desc);
            case "subSequence" -> invokeSubSequence(args, desc);
            case "substring" -> invokeSubstring(args, desc);
            case "toCharArray" -> invokeToCharArray(args, desc);
            case "toLowerCase" -> invokeToLowerCase(args, desc);
            case "toString" -> invokeToString(args, desc);
            case "toUpperCase" -> invokeToUpperCase(args, desc);
            case "transform" -> invokeTransform(args, desc);
            case "translateEscapes" -> invokeTranslateEscapes(args, desc);
            case "trim" -> invokeTrim(args, desc);
            default -> PlaceHolder.instance;
        };
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Init">Init</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeInit(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#CharAt">CharAt</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeCharAt(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            IntValue index = args[0].asIntValue();
            char result = concrete.charAt(index.concrete);
            return new CharValue(context, result, smgr.charAt(formula, index.formula));
        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Chars">Chars</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeChars(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#CodePointAt">CodePointAt</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeCodePointAt(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#CodePointBefore">CodePointBefore</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeCodePointBefore(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#CodePointCount">CodePointCount</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeCodePointCount(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#CodePoints">CodePoints</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeCodePoints(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#CompareTo">CompareTo</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeCompareTo(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#CompareToIgnoreCase">CompareToIgnoreCase</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeCompareToIgnoreCase(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Concat">Concat</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeConcat(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            StringValue str = args[0].asStringValue();
            String result = concrete.concat(str.concrete);
            return new StringValue(context, result, smgr.concat(formula, str.formula), -1);
        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Contains">Contains</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeContains(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1 && args[0] instanceof StringValue s) {
            boolean result = concrete.contains(s.concrete);
            return new BooleanValue(context, result, smgr.contains(formula, s.formula));
        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ContentEquals">ContentEquals</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeContentEquals(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#DescribeConstable">DescribeConstable</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeDescribeConstable(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#EndsWith">EndsWith</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeEndsWith(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            StringValue suffix = args[0].asStringValue();
            boolean result = concrete.startsWith(suffix.concrete);
            return new BooleanValue(context, result, smgr.suffix(suffix.formula, formula));
        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Equals">Equals</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeEquals(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            Value<?, ?> anObject = args[0];
            try {
                StringValue str = anObject.asStringValue();
                boolean result = concrete.equals(str.concrete);
                return new BooleanValue(context, result, smgr.equal(formula, str.formula));
            } catch (Exception ignored) {
                return PlaceHolder.instance;
            }
        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#EqualsIgnoreCase">EqualsIgnoreCase</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeEqualsIgnoreCase(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Formatted">Formatted</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeFormatted(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#GetBytes">GetBytes</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeGetBytes(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#GetChars">GetChars</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeGetChars(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 4) {
            try {
                IntValue srcBegin = args[0].asIntValue();
                IntValue srcEnd = args[1].asIntValue();
                CharArrayValue dst = args[2].asObjectValue().asArrayValue().asCharArrayValue();
                IntValue dstBegin = args[3].asIntValue();
                for (int idx = srcBegin.concrete; idx < srcEnd.concrete; idx++) {
                    Value<?, ?>[] charAtArgs = new Value[] {new IntValue(context, idx)};
                    Type[] charAtDesc = new Type[] {Type.INT_TYPE};
                    dst.storeElement(
                            new IntValue(context, dstBegin.concrete + idx),
                            (CharValue) invokeCharAt(charAtArgs, charAtDesc));
                }
                return VoidValue.instance;
            } catch (Exception ignored) {

                return PlaceHolder.instance;
            }

        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#HashCode">HashCode</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeHashCode(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Indent">Indent</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeIndent(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#IndexOf">IndexOf</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeIndexOf(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            return switch (desc[0].getDescriptor()) {
                case "I" -> invokeIndexOf(args[0].asIntValue());
                case "Ljava/lang/String;" -> invokeIndexOf(args[0].asStringValue());
                default -> PlaceHolder.instance;
            };
        } else if (args.length == 2) {
            return switch (desc[0].getDescriptor()) {
                case "I" -> invokeIndexOf(args[0].asIntValue(), args[1].asIntValue());
                case "Ljava/lang/String;" -> invokeIndexOf(
                        args[0].asStringValue(), args[1].asIntValue());
                default -> PlaceHolder.instance;
            };
        } else {
            return PlaceHolder.instance;
        }
    }

    private Value<?, ?> invokeIndexOf(StringValue str) {
        return invokeIndexOf(str, new IntValue(context, 0));
    }

    private Value<?, ?> invokeIndexOf(StringValue str, IntValue fromIndex) {
        return new IntValue(
                context,
                concrete.indexOf(str.concrete, fromIndex.concrete),
                smgr.indexOf(formula, str.formula, fromIndex.formula));
    }

    private Value<?, ?> invokeIndexOf(IntValue ch) {
        return invokeIndexOf(ch, new IntValue(context, 0));
    }

    private Value<?, ?> invokeIndexOf(IntValue ch, IntValue fromIndex) {
        return invokeIndexOf(ch.asCharStringValue(), fromIndex);
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Intern">Intern</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeIntern(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#IsBlank">IsBlank</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeIsBlank(Value<?, ?>[] args, Type[] desc) {
        StringValue strValue = (StringValue) this;
        IntegerFormulaManager imgr = context.getFormulaManager().getIntegerFormulaManager();

        // Concrete evaluation: checks if the string is empty or whitespace only
        boolean concreteResult = strValue.concrete.isBlank();

        // Symbolic evaluation: create a symbolic version of isBlank
        // This can be more complex as it needs to consider spaces as well as empty strings.
        // As a simplification, let's assume any non-zero length string that does not modify the
        // original string length when trimmed might be considered non-blank
        BooleanFormulaManager bmgr = context.getFormulaManager().getBooleanFormulaManager();

        NumeralFormula.IntegerFormula zero = imgr.makeNumber(0);
        NumeralFormula.IntegerFormula lengthOfTrimmed = imgr.makeNumber(strValue.concrete.trim().length());
        BooleanFormula symbolicResult = bmgr.and(
            imgr.greaterThan(new IntValue(context, strValue.concrete.length()).formula, zero),
            imgr.equal(new IntValue(context, strValue.concrete.length()).formula, lengthOfTrimmed)
        );

        return new BooleanValue(context, concreteResult, symbolicResult);
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#IsEmpty">IsEmpty</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeIsEmpty(Value<?, ?>[] args, Type[] desc) {
        StringValue strValue = (StringValue) this;
        IntegerFormulaManager imgr = context.getFormulaManager().getIntegerFormulaManager();

        boolean concreteResult = strValue.concrete.isEmpty();
        NumeralFormula.IntegerFormula zero = imgr.makeNumber(0);
        BooleanFormula symbolicResult = imgr.equal(new IntValue(context, strValue.concrete.length()).formula, zero);

        return new BooleanValue(context, concreteResult, symbolicResult);
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#LastIndexOf">LastIndexOf</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeLastIndexOf(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Length">Length</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeLength(Value<?, ?>[] args, Type[] desc) {
        return new IntValue(context, concrete.length(), smgr.length(formula));
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Lines">Lines</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeLines(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Matches">Matches</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeMatches(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            StringValue regex = (StringValue) args[0];

            try {
                // Perform the concrete check using String.matches
                boolean concreteResult = this.concrete.matches(regex.concrete);
                BooleanFormulaManager bmgr = context.getFormulaManager().getBooleanFormulaManager();

                // Symbolically represent the match operation
                BooleanFormula matchFormula = bmgr.makeBoolean(concreteResult);

                // Return the result as a BooleanValue
                return new BooleanValue(context, concreteResult, matchFormula);
            } catch (PatternSyntaxException e) {
                // Handle the case where the regular expression's syntax is invalid
                // For symbolic purposes, this can be represented as a placeholder or specific handling
                return PlaceHolder.instance;
            }
        } else {
            return PlaceHolder.instance;
        }    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#OffsetByCodePoints">OffsetByCodePoints</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeOffsetByCodePoints(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#RegionMatches">RegionMatches</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeRegionMatches(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Repeat">Repeat</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeRepeat(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Replace">Replace</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeReplace(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 2) {
            return switch (desc[0].getDescriptor()) {
                case "C" -> invokeReplace(args[0].asCharValue(), args[1].asCharValue());
                case "Ljava/lang/CharSequence;" -> invokeReplace(
                        args[0].asObjectValue(), args[1].asObjectValue());
                default -> PlaceHolder.instance;
            };
        }
        return PlaceHolder.instance;
    }

    private Value<?, ?> invokeReplace(ObjectValue<?, ?> target, ObjectValue<?, ?> replacement) {
        if (target instanceof StringValue s1 && replacement instanceof StringValue s2) {
            // ToDo  (Nils): This is the correct implementation. However replaceAll is currently not
            // supported by Z3
            /*
            this.formula = smgr.replaceAll(this.formula, oldString.formula, newString.formula);
             */
            this.concrete = this.concrete.replace(s1.concrete, s2.concrete);
            for (int i = 0; i < REPLACE_COUNT; i++) {
                this.formula = smgr.replace(this.formula, s1.formula, s2.formula);
            }
            return this;
        } else {
            return PlaceHolder.instance;
        }
    }

    private Value<?, ?> invokeReplace(CharValue oldChar, CharValue newChar) {
        StringValue oldString = oldChar.asStringValue();
        StringValue newString = newChar.asStringValue();
        // ToDo  (Nils): This is the correct implementation. However replaceAll is currently not
        // supported by Z3
        // See: https://git.its.uni-luebeck.de/research-projects/pet-hmr/knife-fuzzer/-/issues/54

        /*
        this.formula = smgr.replaceAll(this.formula, oldString.formula, newString.formula);
         */
        this.concrete = this.concrete.replace(oldString.concrete, newString.concrete);
        for (int i = 0; i < REPLACE_COUNT; i++) {
            this.formula = smgr.replace(this.formula, oldString.formula, newString.formula);
        }
        return this;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ReplaceAll">ReplaceAll</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeReplaceAll(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 2) {
            return switch (desc[0].getDescriptor()) {
                case "Ljava/lang/String;" -> invokeReplaceAll(args[0].asObjectValue(), args[1].asObjectValue());
                default -> PlaceHolder.instance;
            };
        }
        return PlaceHolder.instance;
    }

    private Value<?, ?> invokeReplaceAll(ObjectValue<?, ?> target, ObjectValue<?, ?> replacement) {
        if (target instanceof StringValue s1 && replacement instanceof StringValue s2) {
            this.concrete = this.concrete.replaceAll(s1.concrete, s2.concrete);

            StringFormula currentFormula = this.formula;
            StringFormula newFormula;
            do {
                newFormula = smgr.replace(currentFormula, s1.formula, s2.formula);
                if (!newFormula.equals(currentFormula)) {
                    currentFormula = newFormula;
                } else {
                    break;
                }
            } while (true);
            this.formula = currentFormula;

            return this;
        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ReplaceFirst">ReplaceFirst</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeReplaceFirst(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 2) {
            return invokeReplaceFirst(
                        args[0].asObjectValue(), args[1].asObjectValue());
        }
        return PlaceHolder.instance;
    }

    private Value<?, ?> invokeReplaceFirst(ObjectValue<?, ?> target, ObjectValue<?, ?> replacement) {
        if (target instanceof StringValue s1 && replacement instanceof StringValue s2) {
            this.concrete = this.concrete.replaceFirst(s1.concrete, s2.concrete);
            IntegerFormulaManager imgr = context.getFormulaManager().getIntegerFormulaManager();
            IntegerFormula startIndex = imgr.makeNumber(0);
            IntegerFormula firstIndex = smgr.indexOf(this.formula, s1.formula,startIndex);

            if (firstIndex != null) {
                // Create new formula by combining substrings and replacement
                StringFormula before = smgr.substring(this.formula, startIndex, firstIndex);
                StringFormula after = smgr.substring(this.formula, imgr.add(firstIndex, smgr.length(s1.formula)), smgr.length(this.formula));
                this.formula = smgr.concat(before, smgr.concat(s2.formula, after));
            }
            return this;
        } else {
            return PlaceHolder.instance;
        }
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ResolveConstantDesc">ResolveConstantDesc</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeResolveConstantDesc(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Split">Split</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeSplit(Value<?, ?>[] args, Type[] desc) {
        symbolicStateArray = SymbolicTraceHandlerStore.getInstance().getTraceHandler(args, desc);
        if (symbolicStateArray == null){
            SymbolicTraceHandler handler = new SymbolicTraceHandler();
            int iid = 0; //as it's the first element, give the iid 0
            handler.addInput(this.concrete, this);
            SymbolicTraceHandlerStore.getInstance().setTraceHandler(args, desc, handler, iid);
            symbolicStateArray = SymbolicTraceHandlerStore.getInstance().getTraceHandler(args, desc);
            System.out.println(symbolicStateArray);
        }
        if (args.length == 1) {
            return invokeSplit(args[0].asStringValue());
        } else if (args.length == 2) {
            return invokeSplit(args[0].asStringValue(), args[1].asIntValue());
        } else {
            return PlaceHolder.instance;
        }
    }

    private Value<?, ?> invokeSplit(StringValue regex) {
        //Create prover env to support boolean formula in substring
        try (ProverEnvironment prover = context.newProverEnvironment(ProverOptions.GENERATE_MODELS)){

            // get formulaManagers
            IntegerFormulaManager imgr = context.getFormulaManager().getIntegerFormulaManager();
            BooleanFormulaManager bmgr = context.getFormulaManager().getBooleanFormulaManager();
            FormulaManager fmgr = context.getFormulaManager();

            // setup branch condition handler
            SymbolicTraceHandler sth = (SymbolicTraceHandler) symbolicStateArray[0];
            int iid = ((Integer) symbolicStateArray[1]).intValue();

            // new element constraint collector
            ArrayList<BooleanFormula> trueConditions = new ArrayList<BooleanFormula>();
            ArrayList<BooleanFormula> falseConditions = new ArrayList<BooleanFormula>();

            // to store StringValues in the array -- store to the StringArrayValue at the end
            ArrayList<StringValue> valueArray = new ArrayList<StringValue>();

            // to store all concrete strings
            ArrayList<String> concreteArray = new ArrayList<String>();

            // run concrete split
            String[] concreteResults = concrete.split(regex.concrete);
            System.out.println("Concrete Length: " + concreteResults.length);
            // store all to concreteArray
            for (String s : concreteResults) {
              concreteArray.add(s);
            }

            // start of the string would be always zero
            IntegerFormula startIndex = imgr.makeNumber(0);
            IntegerFormula prevStartIndex = null;
            // create the length of split regex
            IntegerFormula regexLength = imgr.makeNumber(getModifiedUtf8Length(regex.concrete, true));
            IntegerFormula stringEndIndex = null;

            long totalStringLength = this.concrete.length();
            int consumeCount = 0;

            boolean delimiterAddedAtTheEnd = false;

            InputElement ie = sth.getFirstInputElement();
            System.out.println("Input element: " + ie);
            ArrayList<String> hardConstraintsOnInput = ie.getHardConstraints();
            IntegerFormula lastSplitStringLength = null;
            BooleanFormula collectedFormula = bmgr.makeTrue();
            // build the current split strings
            for (int i = 0; i < concreteResults.length; i++) {

                // process concreteResults[i]
                // add string consume count (java length)
                consumeCount += concreteResults[i].length();

                // n-th split
                // start, variableSubstringLength
                String variableSubstringLengthName = "I_" + VariableCount.getInstance().getIncrementedCount();
                IntegerFormula variableSubstringLength = imgr.makeVariable(variableSubstringLengthName);
                
                // could be zero length
                BooleanFormula variableSubstringLengthGTEZero = imgr.greaterOrEquals(variableSubstringLength, imgr.makeNumber(0));
                collectedFormula = bmgr.and(collectedFormula, variableSubstringLengthGTEZero);
                BooleanFormula variableSubstringLengthGTEOne = imgr.greaterOrEquals(variableSubstringLength, imgr.makeNumber(1));
                
                StringFormula splitSubstringFormula = smgr.substring(formula, startIndex, variableSubstringLength);

                IntegerFormula splitSubstringLengthFormula = smgr.length(splitSubstringFormula);
                lastSplitStringLength = splitSubstringLengthFormula;
                BooleanFormula splitSubstringLengthEqualToVariable = imgr.equal(variableSubstringLength, splitSubstringLengthFormula);
                collectedFormula = bmgr.and(collectedFormula, splitSubstringLengthEqualToVariable);

                // substring should not contain delimiter
                /*
                StringFormula firstCharacterFormula = smgr.charAt(splitSubstringFormula, imgr.makeNumber(0));
                BooleanFormula firstNotDelimiter = bmgr.and(bmgr.not(smgr.equal(firstCharacterFormula, regex.formula)), variableSubstringLengthGTEOne);
                BooleanFormula firstNotDelimiter = bmgr.and(bmgr.not(smgr.equal(firstCharacterFormula, regex.formula)), variableSubstringLengthGTEOne);
                collectedFormula = bmgr.and(collectedFormula, firstNotDelimiter);
                */
                //BooleanFormula splitSubstringBooleanFormula = smgr.equal(splitSubstringFormula, splitSubstringFormula);
                //BooleanFormula splitSubstringNotContainsDelimiter = bmgr.not(smgr.contains(splitSubstringFormula, regex.formula));
                //collectedFormula = bmgr.and(collectedFormula, splitSubstringBooleanFormula);
        
                startIndex = imgr.add(startIndex, variableSubstringLength);

                prover.addConstraint(collectedFormula);

                if (prover.isUnsat()) {
                    System.out.println("Condition is unsatisfiable, hence false: " + collectedFormula);
                    return PlaceHolder.instance;
                } else {
                    System.out.println("Condition is satisfiable, hence true: " + collectedFormula);
                    // create split string value
                    StringValue splitStringValue = new StringValue(context, concreteResults[i], fmgr.simplify(splitSubstringFormula), -1);
                    valueArray.add(splitStringValue);

                    // if exist remaining string values..
                    //if (i != concreteResults.length() - 1) {
                    // if not the last entry
                    //if (consumeCount < totalStringLength) {
                    if (i != concreteResults.length - 1) {
                        StringFormula delimiterSubstring = smgr.substring(formula, startIndex, regexLength);
                        BooleanFormula isDelimiter = smgr.equal(delimiterSubstring, regex.formula);
                        collectedFormula = bmgr.and(collectedFormula, isDelimiter);

                        consumeCount += regex.concrete.length();

                        prover.addConstraint(isDelimiter);
                        if (prover.isUnsat()) {
                            System.out.println("Delimiter condition is unsatisfiable: " + isDelimiter);
                            return PlaceHolder.instance;
                        } else {
                            System.out.println("Delimiter found at correct position: " + isDelimiter);
                        }

                        startIndex = imgr.add(startIndex, regexLength);
                        //startIndex = delimiterEndIndex;
                    }
                    else {
                        if (consumeCount < totalStringLength) {
                            System.out.println("Concrete string: " + this.concrete);
                            System.out.println("concrete_string[" + consumeCount + "] = " + this.concrete.charAt(consumeCount));
                            System.out.println("regex concrete : " + regex.concrete);
                            assert this.concrete.charAt(consumeCount) == regex.concrete.charAt(0);
                            StringFormula delimiterSubstring = smgr.substring(formula, stringEndIndex, regexLength);
                            BooleanFormula isDelimiter = smgr.equal(delimiterSubstring, regex.formula);
                            collectedFormula = bmgr.and(collectedFormula, isDelimiter);
                            consumeCount += regex.concrete.length();

                            prover.addConstraint(isDelimiter);
                            if (prover.isUnsat()) {
                                System.out.println("Delimiter condition is unsatisfiable: " + isDelimiter);
                                return PlaceHolder.instance;
                            } else {
                                System.out.println("Delimiter found at correct position: " + isDelimiter);
                            }

                            startIndex = imgr.add(startIndex, regexLength);
                            delimiterAddedAtTheEnd = true;
                        }
                        /*
                        IntegerFormula wholeLengthFormula = smgr.length(this.formula);
                        BooleanFormula wholeLengthEqual = imgr.equal(startIndex, wholeLengthFormula);
                        collectedFormula = bmgr.and(collectedFormula, wholeLengthEqual);
                        */
                        hardConstraintsOnInput.add(fmgr.dumpFormula(fmgr.simplify(collectedFormula)).toString());
                        //trueConditions.add(collectedFormula);
                        collectedFormula = bmgr.makeTrue();

                        // add delimiter at the end
                        //stringEndIndex = imgr.add(startIndex, variableSubstringLength);
                    }
                }
            }
            int MAX_ARRAY_SIZE = concreteResults.length + 1;
            int MAX_SPLIT = 0;
            int MAX_STRING_LENGTH = 256;
            int cnt = 0;
            for (int i = concreteResults.length; i < MAX_ARRAY_SIZE; i++) {
              if (i > MAX_SPLIT) {
                break;
              }
              System.out.println("Adding place holder split string at index " + i);

              if (delimiterAddedAtTheEnd == false) {
                  StringFormula endDelimiterSubstringFormula = smgr.substring(formula, startIndex, regexLength);
                  BooleanFormula endDelimiterEqualFormula = smgr.equal(endDelimiterSubstringFormula, regex.formula);
                  collectedFormula = bmgr.and(endDelimiterEqualFormula, collectedFormula);
                  
                  IntegerFormula delimiterEndIndex = imgr.add(startIndex, regexLength);
                  startIndex = delimiterEndIndex;
                  delimiterAddedAtTheEnd = true;        // run once
              }


              // create split entry length variable
              String variableNameSplitEntry = "I_" + VariableCount.getInstance().getIncrementedCount();
              IntegerFormula stringSplitEntryLength = imgr.makeVariable(variableNameSplitEntry);
              // it should be bigger than one
              BooleanFormula stringLengthGTEOne = imgr.greaterOrEquals(stringSplitEntryLength, imgr.makeNumber(1));
              collectedFormula = bmgr.and(collectedFormula, stringLengthGTEOne);

              // create split entry -- does not contain delimiter
              StringFormula stringSplitEntryFormula = smgr.substring(formula, startIndex, stringSplitEntryLength);
              //StringFormula jazzeFormula = smgr.makeString("jazze");

              //BooleanFormula nullEqualFormula = smgr.equal(stringSplitEntryFormula, jazzeFormula);
              //collectedFormula = bmgr.and(collectedFormula, nullEqualFormula);

              stringEndIndex = imgr.add(startIndex, stringSplitEntryLength);
              IntegerFormula totalStringLengthFormula = smgr.length(formula);
              BooleanFormula stringEndsAtLastDelimiterFormula = imgr.equal(totalStringLengthFormula, stringEndIndex);
              collectedFormula = bmgr.and(collectedFormula, stringEndsAtLastDelimiterFormula);

              falseConditions.add(collectedFormula);
              //hardConstraintsOnInput.add(fmgr.dumpFormula(fmgr.simplify(collectedFormula)).toString());
              //trueConditions.add(collectedFormula);
              collectedFormula = bmgr.makeTrue();

              int regexConcreteLength = (int) getModifiedUtf8Length(regex.concrete, true);
              String placeholder = "Z";
              String withDelimiter = placeholder + regex.concrete;
              //StringValue segment = new StringValue(context, withDelimiter, fmgr.simplify(stringSplitEntryFormula), -1);
              StringValue segment = new StringValue(context, withDelimiter, fmgr.simplify(stringSplitEntryFormula), -1);
              concreteArray.add(withDelimiter);
              valueArray.add(segment);

              break;
            }

            // prepare concrete and StringValue arrays
            String[] concreteRegularArray = new String[concreteArray.size()];
            for (int i=0; i<concreteArray.size(); ++i) {
              concreteRegularArray[i] = concreteArray.get(i);
            }
            StringValue[] valueRegularArray = new StringValue[valueArray.size()];
            for (int i=0; i<valueArray.size(); ++i) {
              valueRegularArray[i] = valueArray.get(i);
            }

            // Create StringArrayValue
            StringArrayValue splitResults = new StringArrayValue(context,
                new IntValue(context, concreteRegularArray.length),
                -1);
            // set concrete array
            splitResults.concrete = concreteRegularArray;

            // set StringValue elements
            for (int i=0; i<valueRegularArray.length; ++i) {
              splitResults.storeElement(new IntValue(context, i), valueRegularArray[i]);
            }

            //sth.checkAndSetBranch(false, fmgr.simplify(collectedFormula), iid);
            for (BooleanFormula bf : trueConditions) {
              System.out.println("True: " + bf);
              sth.checkAndSetBranch(true, fmgr.simplify(bf), SymbolicTraceHandler.getTrueVirtualBranchIID(iid));
            }

            for (BooleanFormula bf : falseConditions) {
              System.out.println("False: " + bf);
              sth.checkAndSetBranch(false, fmgr.simplify(bf), SymbolicTraceHandler.getFalseVirtualBranchIID(iid));
            }

            System.out.println("Returning " + splitResults.formula.toString());
            return splitResults;
        } catch (Exception e) {
            System.out.println(e.getMessage());
            e.printStackTrace();
            return PlaceHolder.instance;
        }
    }

    private Value<?, ?> invokeSplit(StringValue regex, IntValue limit) {
        //Create prover env to support boolean formula in substring
        try (ProverEnvironment prover = context.newProverEnvironment(ProverOptions.GENERATE_MODELS)){
            String[] concreteResults = concrete.split(regex.concrete, limit.concrete);
            StringArrayValue splitResults = new StringArrayValue(context, limit, concreteResults.hashCode());
            splitResults.concrete = concreteResults;
            String[] concreteResultsReal = concrete.split(regex.concrete);
            Boolean limited = false;
            if (concreteResults.length < concreteResultsReal.length)
                limited = true;
            IntegerFormulaManager imgr = context.getFormulaManager().getIntegerFormulaManager();
            IntegerFormula startIndex = imgr.makeNumber(0);
            BooleanFormulaManager bmgr = context.getFormulaManager().getBooleanFormulaManager();
            IntegerFormula regexLength = imgr.makeNumber(getModifiedUtf8Length(regex.concrete, true));


            for (int i = 0; i < concreteResults.length; i++) {

                IntegerFormula length = imgr.makeNumber(getModifiedUtf8Length(concreteResults[i], true));
                StringFormula substringFormula = smgr.substring(formula, startIndex, length);
                BooleanFormula notContainsDelimiter = bmgr.not(smgr.contains(substringFormula, regex.formula));
                IntegerFormula endIndex = imgr.add(startIndex, length);

                // We should not assume the last part does not contain delimiter as we approach the split limit
                if(i!=concreteResults.length-1 && limited)
                    prover.addConstraint(notContainsDelimiter);

                if (prover.isUnsat()) {
                    System.out.println("Condition is unsatisfiable, hence false.");
                    return PlaceHolder.instance;
                } else {
                    System.out.println("Condition is satisfiable, hence true.");
                    // Handle satisfying segment
                    StringValue segment = new StringValue(context, concreteResults[i], substringFormula, substringFormula.hashCode());
                    splitResults.storeElement(new IntValue(context, i), segment);

                    // Prepare for next iteration
                    if (i < concreteResults.length - 1) {  // Exclude the last iteration
                        IntegerFormula delimiterEndIndex = imgr.add(endIndex, regexLength);
                        IntegerFormula delimiterIndex = smgr.indexOf(formula, regex.formula, endIndex);
                        BooleanFormula isDelimiterAtEndIndex = imgr.equal(delimiterIndex, endIndex);
                        prover.addConstraint(isDelimiterAtEndIndex);

                        if (prover.isUnsat()) {
                            System.out.println("Delimiter condition is unsatisfiable.");
                            return PlaceHolder.instance;
                        } else {
                            System.out.println("Delimiter found at correct position.");
                        }
                        startIndex = delimiterEndIndex;
                    }

                }

            }

            return splitResults;
        } catch (Exception e) {
            return PlaceHolder.instance;
        }
    }


    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#StartsWith">StartsWith</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeStartsWith(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            return invokeStartsWith(args[0].asStringValue());
        } else if (args.length == 2) {
            return invokeStartsWith(args[0].asStringValue(), args[1].asIntValue());
        } else {
            return PlaceHolder.instance;
        }
    }

    private Value<?, ?> invokeStartsWith(StringValue prefix) {
        return new BooleanValue(
                context,
                concrete.startsWith(prefix.concrete),
                smgr.prefix(prefix.formula, formula));
    }

    private Value<?, ?> invokeStartsWith(StringValue prefix, IntValue toffset) {
        return new BooleanValue(
                context,
                concrete.startsWith(prefix.concrete),
                smgr.equal(
                        prefix.formula,
                        smgr.substring(formula, toffset.formula, smgr.length(prefix.formula))));
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Strip">Strip</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeStrip(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#StripIndent">StripIndent</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeStripIndent(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#StripLeading">StripLeading</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeStripLeading(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#StripTrailing">StripTrailing</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeStripTrailing(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#SubSequence">SubSequence</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeSubSequence(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Substring">Substring</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeSubstring(Value<?, ?>[] args, Type[] desc) {
        if (args.length == 1) {
            return invokeSubstring(args[0].asIntValue());
        } else if (args.length == 2) {
            return invokeSubstring(args[0].asIntValue(), args[1].asIntValue());
        } else {
            return PlaceHolder.instance;
        }
    }

    private Value<?, ?> invokeSubstring(IntValue beginIndex) {
        IntValue endIndex = new IntValue(context, concrete.length(), smgr.length(this.formula));
        return invokeSubstring(beginIndex, endIndex);
    }

    private Value<?, ?> invokeSubstring(IntValue beginIndex, IntValue endIndex) {
        IntegerFormulaManager imgr = context.getFormulaManager().getIntegerFormulaManager();
        return new StringValue(
                context,
                concrete.substring(beginIndex.concrete, endIndex.concrete),
                smgr.substring(
                        formula,
                        beginIndex.formula,
                        imgr.subtract(endIndex.formula, beginIndex.formula)),
                -1);
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ToCharArray">ToCharArray</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeToCharArray(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ToLowerCase">ToLowerCase</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeToLowerCase(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ToString">ToString</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeToString(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#ToUpperCase">ToUpperCase</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeToUpperCase(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Transform">Transform</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeTransform(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#TranslateEscapes">TranslateEscapes</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeTranslateEscapes(Value<?, ?>[] args, Type[] desc) {
        return PlaceHolder.instance;
    }

    /**
     * Invocation handling for the String instance method <a
     * href="https://docs.oracle.com/en/java/javase/16/docs/api/java.base/java/lang/String.html#Trim">Trim</a>().
     * Returns PlaceHolder::instance if the method is not yet implemented, or the Value that
     * represents the result of the method including symbolic handling.
     *
     * @param args List of Values that correspond to the method arguments
     * @param desc Array of Type descriptions of the methods' signature. No guarantee is given that
     *     the Value in args is of the same type.
     * @return The resulting Value or PlaceHolder::instance
     */
    private Value<?, ?> invokeTrim(Value<?, ?>[] args, Type[] desc) {
        //return PlaceHolder.instance;
        return this;
    }

    @Override
    public String getConcreteEncoded() {
        char[] chars = concrete.toCharArray();
        int[] tmp = new int[chars.length];
        for (int i = 0; i < chars.length; i++) {
            tmp[i] = chars[i];
        }
        return Arrays.toString(tmp);
    }

    @Override
    public StringValue asStringValue() {
        return this;
    }

    @Override
    public StringValue asObjectValue() {
        return this;
    }

    @Override
    public String toString() {
        String formulaString = null != formula ? this.formula.toString() : "";
        String concreteString = null != concrete ? concrete : "";

        if (formulaString.length() > Config.instance().getLoggingFormulaLength()) {
            formulaString =
                    formulaString.substring(0, Config.instance().getLoggingFormulaLength()) + "...";
        }

        return "Ljava/lang/String; @"
                + Integer.toHexString(address)
                + " ("
                + concreteString
                + ", "
                + formulaString
                + ")";
    }
}
