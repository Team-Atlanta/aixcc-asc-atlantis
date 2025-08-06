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

/**
 * This is dangerous to use for fuzzing because it executes as a command a string generated from
 * the fuzzer.
 * However, as a sanitizer, we do want to allow processes to be forked, as long as they
 * aren't the SENTINEL, obv...
 */
public class OsCommandInjection {

    public static final String ENV_KEY = "JAZZER_COMMAND_INJECTION";
    public static final String DEFAULT_SENTINEL = "jazze";
    public static final String SENTINEL =
            (System.getenv(ENV_KEY) == null || System.getenv(ENV_KEY).trim().length() == 0) ?
                    DEFAULT_SENTINEL : System.getenv(ENV_KEY);

    @MethodHook(
        type = HookType.BEFORE,
        targetClassName = "java.lang.ProcessImpl",
        targetMethod = "start",
        additionalClassesToHook = {"java.lang.ProcessBuilder"}
    )
    public static void ProcessImplStartHook (MethodHandle handle, Object thisObject, Object[] args,
                                          int hookId) throws IOException {
        String[] cmd_line_args = (String[])(args[0]);
        for (int i=0; i < cmd_line_args.length; i++) {
            if (SENTINEL.equals(cmd_line_args[i])) {
                Jazzer.reportFindingFromHook(
                    new FuzzerSecurityIssueCritical(
                        String.format("OS Command Injection\nExecuting OS commands with attacker-controlled data can lead to remote code execution.\nFound in argument " + i))
                );
            } else if (i == 0) {
                Jazzer.guideTowardsEquality(cmd_line_args[i], SENTINEL, hookId);
            }
        }

        String fuzz_input = "";
        for (int i=0; i < cmd_line_args.length; i++) {
            fuzz_input.concat(cmd_line_args[i]);
        }
        Jazzer.guideTowardsContainment(fuzz_input, SENTINEL, hookId);
    }
}
