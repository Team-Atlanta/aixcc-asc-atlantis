package com.code_intelligence.jazzer.sanitizers;

import java.io.IOException;
import static java.util.Collections.unmodifiableSet;
import com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical;
import com.code_intelligence.jazzer.api.HookType;
import com.code_intelligence.jazzer.api.Jazzer;
import com.code_intelligence.jazzer.api.MethodHook;
import java.lang.invoke.MethodHandle;
import java.util.Set;
import java.util.Arrays;
import java.util.List;

public class IntegerOverflow {
    @MethodHook(type = HookType.BEFORE, targetClassName = "com.code_intelligence.jazzer.runtime.TraceDataFlowNativeCallbacks",
        targetMethod = "traceAddIntWrapper", targetMethodDescriptor = "(III)I")
    public static void hookTraceAddIntWrapper(MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        int value1 = (int) arguments[0];
        int value2 = (int) arguments[1];
        long a = (long) value1;
        long b = (long) value2;
        if ((a + b) != (long)(value1+value2)) {
            Jazzer.reportFindingFromHook(
                new FuzzerSecurityIssueCritical(
                    String.format("Integer Overflow(addition) detected! REASON: " + value1 + " + " + value2 + " == (int)" + (value1+value2) + " != (long)" + (a+b)))
            );
        }
    }

    @MethodHook(type = HookType.BEFORE, targetClassName = "com.code_intelligence.jazzer.runtime.TraceDataFlowNativeCallbacks",
        targetMethod = "traceSubIntWrapper", targetMethodDescriptor = "(III)I")
    public static void hookTraceSubIntWrapper(MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        int value1 = (int) arguments[0];
        int value2 = (int) arguments[1];
        long a = (long) value1;
        long b = (long) value2;
        if ((a - b) != (long)(value1-value2)) {
            Jazzer.reportFindingFromHook(
                new FuzzerSecurityIssueCritical(
                    String.format("Integer Underflow(subtraction) detected! REASON: " + value1 +
                            " - " + value2 + " == (int)" + (value1-value2) + " != (long)" + (a-b)))
            );
        }
    }

    @MethodHook(type = HookType.BEFORE, targetClassName = "com.code_intelligence.jazzer.runtime.TraceDataFlowNativeCallbacks",
        targetMethod = "traceMulIntWrapper", targetMethodDescriptor = "(III)I")
    public static void hookTraceMulIntWrapper(MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        int value1 = (int) arguments[0];
        int value2 = (int) arguments[1];
        long a = (long) value1;
        long b = (long) value2;
        if ((a * b) != (long)(value1*value2)) {
            Jazzer.reportFindingFromHook(
                new FuzzerSecurityIssueCritical(
                    String.format("Integer Overflow(multiplication) detected! REASON: " + value1 + " * " + value2 + " == (int)" + (value1*value2) + " != (long)" + (a*b)))
            );
        }
    }

    @MethodHook(type = HookType.BEFORE, targetClassName = "com.code_intelligence.jazzer.runtime.TraceDataFlowNativeCallbacks",
        targetMethod = "traceDivIntWrapper", targetMethodDescriptor = "(III)I")
    public static void hookTraceDivIntWrapper(MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        int value1 = (int) arguments[0];
        int value2 = (int) arguments[1];
        long a = (long) value1;
        long b = (long) value2;
        if ((a / b) != (long)(value1/value2)) {
            Jazzer.reportFindingFromHook(
                new FuzzerSecurityIssueCritical(
                    String.format("Integer Overflow(division) detected! REASON: " + value1 + " / " + value2 + " == (int)" + (value1/value2) + " != (long)" + (a/b)))
            );
        }
    }
}