/*
 * Copyright 2024 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.code_intelligence.jazzer.sanitizers

import com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical
import com.code_intelligence.jazzer.api.HookType
import com.code_intelligence.jazzer.api.Jazzer
import com.code_intelligence.jazzer.api.MethodHook
import com.code_intelligence.jazzer.api.MethodHooks
import java.lang.invoke.MethodHandle

/**
 * XSS Sanitizer specifically made for Jenkin's web page output.
 */
@Suppress("unused_parameter", "unused")
object JenkinsXss {

    private const val XSS_ATTACK = "<script>alert(1)"
    private const val XSS_ATTR_ATTACK = "onmouseover=alert(1)"

    // Guide the fuzzer towards including the xss attack
    @MethodHooks(
        MethodHook(
            type = HookType.BEFORE,
            targetClassName = "hudson.AbstractMarkupText",
            targetMethod = "addMarkup",
        ),
    )
    @JvmStatic
    fun addMarkup(method: MethodHandle, thisObject: Any?, args: Array<Any>, hookId: Int) {
        val startTag = args[2] as String
        Jazzer.guideTowardsContainment(startTag, XSS_ATTACK, hookId)
        // Times 31 copied from NamingContextLookup sanitizer.
        Jazzer.guideTowardsContainment(startTag, XSS_ATTR_ATTACK, hookId * 31)
    }

    // Check if the final output contains the xss attack string and throw
    // a finding if so.
    @MethodHooks(
        // Single object lookup, possible DN injection
        MethodHook(
            type = HookType.REPLACE,
            targetClassName = "hudson.AbstractMarkupText",
            targetMethod = "toString",
            targetMethodDescriptor = "(Z)Ljava/lang/String;",
        ),
    )
    @JvmStatic
    fun markupToString(method: MethodHandle, thisObject: Any?, args: Array<Any>, hookId: Int): Any? {
        val htmlOutput = method.invokeWithArguments(thisObject, *args) as String

        if (htmlOutput.contains(XSS_ATTACK) || htmlOutput.contains(XSS_ATTR_ATTACK)) {
            Jazzer.reportFindingFromHook(
                FuzzerSecurityIssueCritical(
                    String.format("Xss injection%nOutput: %s%n", htmlOutput),
                ),
            )
        }
        return htmlOutput
    }
}