package de.uzl.its.value.reference


import de.uzl.its.swat.symbolic.value.Value
import de.uzl.its.swat.symbolic.value.VoidValue;
import de.uzl.its.swat.symbolic.value.primitive.numeric.floatingpoint.DoubleValue
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.CharValue
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.IntValue
import de.uzl.its.swat.symbolic.value.primitive.numeric.integral.BooleanValue;
import de.uzl.its.swat.symbolic.value.reference.StringBuilderValue
import de.uzl.its.swat.symbolic.value.reference.lang.StringValue

import de.uzl.its.swat.symbolic.value.reference.array.StringArrayValue
import de.uzl.its.swat.symbolic.value.reference.array.CharArrayValue;

import org.objectweb.asm.Type
import org.sosy_lab.common.ShutdownManager
import org.sosy_lab.common.configuration.Configuration
import org.sosy_lab.common.log.BasicLogManager
import org.sosy_lab.java_smt.SolverContextFactory
import org.sosy_lab.java_smt.api.SolverContext
import org.sosy_lab.java_smt.api.StringFormula
import spock.lang.Ignore
import spock.lang.Specification

class StringBuilderValueTest extends Specification {

    def context =
            SolverContextFactory.createSolverContext(
                    Configuration.defaultConfiguration(),
                    BasicLogManager.create(Configuration.defaultConfiguration()),
                    ShutdownManager.create().getNotifier(),
                    SolverContextFactory.Solvers.Z3)
    def prover = context.newProverEnvironment(
            SolverContext.ProverOptions.GENERATE_MODELS)
    def bmgr = context.getFormulaManager().getBooleanFormulaManager()
    def imgr = context.getFormulaManager().getIntegerFormulaManager()
    def smgr = context.getFormulaManager().getStringFormulaManager()

    def "substring(int start)" () {
        setup:
        prover.push()
        int start = 2
        def exampleString = "abcdefghijk"
        String exampleSubstring = exampleString.substring(start)
        def startIndex = new IntValue(context, start)
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE] as Type[]
        def args = [startIndex] as Value<?, ?>[]

        when:
        def stringValue = (StringValue) stringBuilderValue.invokeMethod("substring", desc, args)
        prover.addConstraint(smgr.equal(stringValue.formula,
                smgr.makeString(exampleSubstring)))

        then:
        stringValue.concrete == exampleSubstring
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "append(CharSequence s)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        def appendString = "appending..."
        def appendStringValue = new StringValue(context, appendString, -1)
        def exampleAppendedString = new StringBuilder(exampleString).append(appendString).toString()
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.getType(String.class)] as Type[]
        def args = [appendStringValue] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("append", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(exampleAppendedString)))

        then:
        stringBuilderValue.stringValue.concrete == exampleAppendedString
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "append(char c)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        char appendChar = 'a'
        def appendCharValue = new CharValue(context, appendChar)
        def exampleAppendedString = new StringBuilder(exampleString).append(appendChar).toString()
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc =[Type.CHAR_TYPE] as Type[]
        def args = [appendCharValue] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("append", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeVariable("str")))//smgr.makeString(exampleAppendedString)))


        then:
        println Type.CHAR_TYPE.getDescriptor()
        println stringBuilderValue.stringValue.formula
        println exampleAppendedString
        stringBuilderValue.stringValue.concrete == exampleAppendedString
        !prover.isUnsat()
        println prover.getModel()

        cleanup:
        prover.pop()
    }

    // ToDo: asStringValue Not implemented yet
    @Ignore
    def "append(double d)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        Double appendDouble = 7.34
        def appendDoubleValue = new DoubleValue(context, appendDouble)
        def exampleAppendedString = new StringBuilder(exampleString).append(appendDouble).toString()
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.DOUBLE_TYPE] as Type[]
        def args = [appendDoubleValue] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("append", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(exampleAppendedString)))

        then:
        stringBuilderValue.stringValue.concrete == exampleAppendedString
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    // ToDo: How about negativ integer values? We could only filter for the concrete value
    def "append(int i)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        Integer appendInteger = 7
        def appendIntegerValue = new IntValue(context, appendInteger)
        def exampleAppendedString = new StringBuilder(exampleString).append(appendInteger).toString()
        println exampleAppendedString
        println Type.INT_TYPE.getDescriptor()
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE] as Type[]
        def args = [appendIntegerValue] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("append",desc , args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(exampleAppendedString)))

        then:
        stringBuilderValue.stringValue.concrete == exampleAppendedString
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "append(CharSequence s, int start, int end)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        int startIndex = 2, endindex = 4
        def appendString = "appending..."
        def appendStringValue = new StringValue(context, appendString, -1)
        def exampleAppendedString = new StringBuilder(exampleString).append(appendString, startIndex, endindex).toString()
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.getType(CharSequence.class),
                    Type.INT_TYPE,
                    Type.INT_TYPE] as Type[]
        def args = [appendStringValue,
                    new IntValue(context, startIndex),
                    new IntValue(context, endindex)] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("append", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(exampleAppendedString)))

        then:
        stringBuilderValue.stringValue.concrete == exampleAppendedString
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "appendCodePoint"() {
        setup:
        prover.push()
        def initialString = "Initial"
        def stringBuilderValue = new StringBuilderValue(context, new StringValue(context, initialString, -1), -1)
        def codePoint = 0x1F600 // Unicode code point for 😀 (grinning face emoji)
        def codePointValue = new IntValue(context, codePoint)
        def desc = [Type.INT_TYPE] as Type[]
        def args = [codePointValue] as Value<?, ?>[]
        
        when:
        def result = stringBuilderValue.invokeAppendCodePoint(args, desc)
        
        then:
        result instanceof StringBuilderValue
        result.stringValue.concrete == new StringBuilder(initialString).append(new String(Character.toChars(codePoint))).toString()

        !prover.isUnsat()
        cleanup:
        prover.pop()
    }

    def "codePointAt"() {
        given:
        def initialString = "Initial😀String"
        def stringValue = new StringValue(context, initialString, -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def index = 7 // Position of the grinning face emoji
        def indexValue = new IntValue(context, index)
        def desc = [Type.INT_TYPE] as Type[]
        def args = [indexValue] as Value<?, ?>[]

        when:
        def result = stringBuilderValue.invokeCodePointAt(args, desc)
        
        then:
        result instanceof IntValue
        println "result is "+result
        result.concrete == initialString.codePointAt(index)
    }

    def "codePointBefore"() {
        given:
        def initialString = "Initial😀String"
        def stringValue = new StringValue(context, initialString, -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def index = 8 // Position of the grinning face emoji
        def indexValue = new IntValue(context, index)
        def desc = [Type.INT_TYPE] as Type[]
        def args = [indexValue] as Value<?, ?>[]

        when:
        def result = stringBuilderValue.invokeCodePointBefore(args, desc)
        
        then:
        result instanceof IntValue
        println "result is "+result
        result.concrete == initialString.codePointBefore(index)
    }

   def "codePointCount"() {
        given:
        def initialString = "Initial😀String"
        def stringValue = new StringValue(context, initialString, -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def beginIndex = 0
        def endIndex = 7 
        def beginIndexValue = new IntValue(context, beginIndex)
        def endIndexValue = new IntValue(context, endIndex)
        def desc = [Type.INT_TYPE, Type.INT_TYPE] as Type[]
        def args = [beginIndexValue, endIndexValue] as Value<?, ?>[]

        when:
        def result = stringBuilderValue.invokeCodePointCount(args, desc)
        
        then:
        result instanceof IntValue
        println "result is $result"
        result.concrete == initialString.codePointCount(beginIndex, endIndex)
    }

    def "charAt(int index)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        int index = 2
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE] as Type[]
        def args = [new IntValue(context, index)] as Value<?, ?>[]

        when:
        CharValue charValue = (CharValue) stringBuilderValue.invokeMethod("charAt", desc, args)
        prover.addConstraint(imgr.equal(charValue.formula,
                imgr.makeNumber(new StringBuilder(exampleString).charAt(index) as Integer)))

        then:
        charValue.concrete == new StringBuilder(exampleString).charAt(index)
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "compareTo with equal strings"() {
        given:
        def stringValue = new StringValue(context, "TestString", -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def otherStringValue = new StringValue(context, "TestString", -1)
        def args = [otherStringValue] as Value<?, ?>[]
        def desc = [Type.getType(String)] as Type[]

        when:
        def result = stringBuilderValue.invokeCompareTo(args, desc)

        then:
        result instanceof IntValue
        result.concrete == 0
    }

    def "compareTo with different strings"() {
        given:
        def stringValue = new StringValue(context, "TestString", -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def otherStringValue = new StringValue(context, "AnotherString", -1)
        def args = [otherStringValue] as Value<?, ?>[]
        def desc = [Type.getType(String)] as Type[]

        when:
        def result = stringBuilderValue.invokeCompareTo(args, desc)

        then:
        result instanceof IntValue
        result.concrete > 0 // "TestString" is lexicographically greater than "AnotherString"
    }

    def "compareTo with empty string"() {
        given:
        def stringValue = new StringValue(context, "TestString", -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def otherStringValue = new StringValue(context, "", -1)
        def args = [otherStringValue] as Value<?, ?>[]
        def desc = [Type.getType(String)] as Type[]

        when:
        def result = stringBuilderValue.invokeCompareTo(args, desc)

        then:
        result instanceof IntValue
        result.concrete > 0 // "TestString" is lexicographically greater than an empty string
    }

    def "ensureCapacity with valid capacity"() {
        given:
        def initialString = "InitialString"
        def stringValue = new StringValue(context, initialString, -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def capacityValue = new IntValue(context, 50)
        def args = [capacityValue] as Value<?, ?>[]
        def desc = [Type.INT_TYPE] as Type[]

        when:
        def result = stringBuilderValue.invokeEnsureCapacity(args, desc)

        then:
        result instanceof VoidValue
        stringBuilderValue.capacity.concrete >= 50
    }

    def "getChars with valid range"() {
        given:
        def initialString = "HelloWorld"
        def stringValue = new StringValue(context, initialString, -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def srcBeginValue = new IntValue(context, 0)
        def srcEndValue = new IntValue(context, 5)
        def destArray = new char[5]
        def destArrayValue = new CharArrayValue(context, destArray, -1)
        def args = [srcBeginValue, srcEndValue, destArrayValue] as Value<?, ?>[]
        def desc = [Type.INT_TYPE, Type.INT_TYPE, Type.getType(char[].class)] as Type[]

        when:
        def result = stringBuilderValue.invokeGetChars(args, desc)

        then:
        result instanceof VoidValue
        destArray == ['H', 'e', 'l', 'l', 'o'] as char[]
    }

    def "indexOf(String str)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        def searchString = "fgh"
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.getType(String.class)] as Type[]
        def args = [new StringValue(context, searchString, -100)]  as Value<?, ?>[]

        when:
        IntValue index = (IntValue) stringBuilderValue.invokeMethod("indexOf", desc, args)
        prover.addConstraint(imgr.equal(index.formula,
                imgr.makeNumber(new StringBuilder(exampleString).indexOf(searchString))))

        then:
        index.getConcrete() == new StringBuilder(exampleString).indexOf(searchString)
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "insert(int offset, String str)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        def insertString = "42"
        def insertOffset = 5
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE, Type.getType(String.class)] as Type[]
        def args =  [new IntValue(context, insertOffset),
                     new StringValue(context, insertString, -1)] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("insert", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(new StringBuilder(exampleString).insert(insertOffset, insertString).toString())))

        then:
        stringBuilderValue.stringValue.concrete == new StringBuilder(exampleString).insert(insertOffset, insertString).toString()
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    // ToDo: asStringValue Not implemented yet
    @Ignore
    def "insert(int offset, double d)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        def insertDouble = 42.42
        def insertOffset = 5
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE, Type.DOUBLE_TYPE] as Type[]
        def args = [new IntValue(context, insertOffset),
                    new DoubleValue(context, insertDouble)] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("insert", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(new StringBuilder(exampleString).insert(insertOffset, insertDouble).toString())))

        then:
        stringBuilderValue.stringValue.concrete == new StringBuilder(exampleString).insert(insertOffset, insertDouble).toString()
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "insert(int offset, char c)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        char insertChar = 'z'
        def insertOffset = 5
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE, Type.CHAR_TYPE] as Type[]
        def args = [new IntValue(context, insertOffset),
                    new CharValue(context, insertChar)] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("insert", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(new StringBuilder(exampleString).insert(insertOffset, insertChar).toString())))

        then:
        stringBuilderValue.stringValue.concrete == new StringBuilder(exampleString).insert(insertOffset, insertChar).toString()
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "insert(int offset, int i)"() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        def insertInteger = 42
        def insertOffset = 5
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE, Type.INT_TYPE] as Type[]
        def args = [new IntValue(context, insertOffset),
                    new IntValue(context, insertInteger)] as Value<?, ?>[]

        when:
        stringBuilderValue.invokeMethod("insert", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(new StringBuilder(exampleString).insert(insertOffset, insertInteger).toString())))

        then:
        stringBuilderValue.stringValue.concrete == new StringBuilder(exampleString).insert(insertOffset, insertInteger).toString()
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "offsetByCodePoints with valid arguments"() {
        given:
        def initialString = "HelloWorld"
        def stringValue = new StringValue(context, initialString, -1)
        def stringBuilderValue = new StringBuilderValue(context, stringValue, -1)
        def indexValue = new IntValue(context, 5)
        def codePointOffsetValue = new IntValue(context, 2)
        def args = [indexValue, codePointOffsetValue] as Value<?, ?>[]
        def desc = [Type.INT_TYPE, Type.INT_TYPE] as Type[]

        when:
        def result = stringBuilderValue.invokeOffsetByCodePoints(args, desc)

        then:
        result instanceof IntValue
        result.concrete == initialString.offsetByCodePoints(5, 2)
    }

    def "replace("() {
        setup:
        prover.push()
        def exampleString = "abcdefghijk"
        def replacementString = "42"
        def startIndex = 1
        def endIndex = 9
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.INT_TYPE, Type.INT_TYPE, Type.getType(String.class)] as Type[]
        def args = [new IntValue(context, startIndex),
                    new IntValue(context, endIndex),
                    new StringValue(context, replacementString, -1)] as Value<?, ?>[]

        when:
        println args
        stringBuilderValue.invokeMethod("replace", desc, args)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(new StringBuilder(exampleString).replace(startIndex, endIndex, replacementString).toString())))

        then:
        stringBuilderValue.stringValue.concrete == new StringBuilder(exampleString).replace(startIndex, endIndex, replacementString).toString()
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }
    def "replaceAll"() {
        setup:
        prover.push()
        def exampleString = "abcabcabc"
        def regexPattern = "abc"
        def replacementString = "42"
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.getType(String.class), Type.getType(String.class)] as Type[]
        def args = [new StringValue(context, regexPattern, -1),
                        new StringValue(context, replacementString, -1)] as Value<?, ?>[]

        when:
        println args
        stringBuilderValue.invokeMethod("replaceAll", desc, args)
        def expectedString = new StringBuilder(exampleString).toString().replaceAll(regexPattern, replacementString)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(expectedString)))

        then:
        println expectedString
        println stringBuilderValue.stringValue.concrete
        stringBuilderValue.stringValue.concrete == expectedString
        !prover.isUnsat()

        cleanup:
        prover.pop()
   }

    def "replaceFirst"() {
        setup:
        prover.push()
        def exampleString = "abcabcabc"
        def regexPattern = "abc"
        def replacementString = "42"
        def stringBuilderValue = new StringBuilderValue(context,
                new StringValue(context, exampleString, -1),
                -1)
        def desc = [Type.getType(String.class), Type.getType(String.class)] as Type[]
        def args = [new StringValue(context, regexPattern, -1),
                        new StringValue(context, replacementString, -1)] as Value<?, ?>[]

        when:
        println args
        stringBuilderValue.invokeMethod("replaceFirst", desc, args)
        def expectedString = new StringBuilder(exampleString).toString().replaceFirst(regexPattern, replacementString)
        prover.addConstraint(smgr.equal((StringFormula) stringBuilderValue.stringValue.formula,
                smgr.makeString(expectedString)))

        then:
        println expectedString
        println stringBuilderValue.stringValue.concrete
        stringBuilderValue.stringValue.concrete == expectedString
        !prover.isUnsat()

        cleanup:
        prover.pop()
     }
     
     @Ignore
     def "split single delimiter"() {
        setup:
        prover.push()
        def exampleString = "hello:world:this:is:a:test"
        def delimiter = ":"
        def stringValue = new StringValue(context, exampleString, -1)
        def stringBuilderValue = new StringBuilderValue(context, new StringValue(context, exampleString, -1), -1)
        def desc = [Type.getType(String.class)] as Type[]
        def args = [new StringValue(context, delimiter, -1)] as Value<?, ?>[]

        when:
        def result = stringValue.invokeMethod("split", desc, args) as StringArrayValue
        def result_2 = stringBuilderValue.invokeMethod("split", desc, args) as StringArrayValue

        def expectedResults = exampleString.split(delimiter)

        then:
        println "Expected Results:  ${expectedResults}"
        println "Actual Results: ${result.concrete_val}"
        println "Actual Results_2: ${result_2.concrete_val}"
        println "the expression for the first one is ${result.formula}"
        println "the expression for the second result is ${result_2.formula}"


        result.concrete_val== expectedResults.append("Z"+delimiter)
        result_2.concrete_val== expectedResults
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }

    def "split with limit"() {
        setup:
        prover.push()
        def exampleString = "hello\0world\0this\0is\0a\0test"
        def delimiter = "\0"
        def limit = 3
        def stringValue = new StringValue(context, exampleString, -1)
        def stringBuilderValue = new StringBuilderValue(context, new StringValue(context, exampleString, -1), -1)

        def desc = [Type.getType(String.class), Type.INT_TYPE] as Type[]
        def args = [new StringValue(context, delimiter, -1),
                    new IntValue(context, limit)] as Value<?, ?>[]

        when:
        def result = stringValue.invokeMethod("split", desc, args) as StringArrayValue
        def result_2 = stringBuilderValue.invokeMethod("split", desc, args) as StringArrayValue
        def expectedResults = exampleString.split(delimiter, limit)
        def expectedLength = expectedResults.length

        then:
        println "Expected Results:  ${expectedResults}"
        println "Actual Results: ${result.concrete_val}"
        println "Actual Results_2: ${result_2.concrete_val}"
        println "the expression for the first one is ${result.formula}"
        println "the expression for the second result is ${result_2.formula}"
        println "the lengh of the array is ${result.length}"

        result.concrete_val== expectedResults
        result_2.concrete_val== expectedResults
        result.length.concrete == expectedLength
        !prover.isUnsat()

        cleanup:
        prover.pop()
    }
    def "test string isEmpty"() {
        setup:

        def emptyString = ""
        def nonEmptyString = "not empty"
        def stringValueEmpty = new StringValue(context, emptyString, -1)
        def stringValueNonEmpty = new StringBuilderValue(context, new StringValue(context,nonEmptyString, -1), -1)

        def desc = [] as Type[]
        def args = [] as Value<?, ?>[]

        when:
        def resultEmpty = stringValueEmpty.invokeMethod("isEmpty", desc, args) 
        def resultNonEmpty = stringValueNonEmpty.invokeMethod("isEmpty", desc, args)
        then:
        println "Testing if empty: ${emptyString}"
        println "Expected: true, Actual: ${resultEmpty}"
        println "Testing if not empty: ${nonEmptyString}"
        println "Expected: false, Actual: ${resultNonEmpty}"

        resultEmpty.concrete == true
        resultNonEmpty.concrete == false
    }

        def "test string isBlank"() {
        setup:
        def emptyString = ""
        def whitespaceString = "   "
        def nonEmptyString = "not empty"
        def stringValueEmpty = new StringValue(context, emptyString, -1)
        def stringValueWhitespace = new StringValue(context, whitespaceString, -1)
        def stringValueNonEmpty = new StringBuilderValue(context, new StringValue(context, nonEmptyString, -1), -1)

        def desc = [] as Type[]
        def args = [] as Value<?, ?>[]

        when:
        def resultEmpty = stringValueEmpty.invokeMethod("isBlank", desc, args) 
        def resultWhitespace = stringValueWhitespace.invokeMethod("isBlank", desc, args)
        def resultNonEmpty = stringValueNonEmpty.invokeMethod("isBlank", desc, args)

        then:
        // Check the results
        println "Testing if empty: ${emptyString}"
        println "Expected: true, Actual: ${resultEmpty.concrete}"
        println "Testing if whitespace: ${whitespaceString}"
        println "Expected: true, Actual: ${resultWhitespace.concrete}"
        println "Testing if not empty: ${nonEmptyString}"
        println "Expected: false, Actual: ${resultNonEmpty.concrete}"

        resultEmpty.concrete == true
        resultWhitespace.concrete == true

        resultNonEmpty.concrete == false
    }
    def "test string matches"() {
        setup:
        def testString = "abc123"
        def regexPattern = "abc\\d+"
        def nonMatchingPattern = "xyz\\d+"
        def stringValueTest = new StringValue(context, testString, -1)

        def desc = [Type.getType(String.class)] as Type[]
        def matchingArgs = [new StringValue(context, regexPattern, -1)] as Value<?, ?>[]
        def nonMatchingArgs = [new StringValue(context, nonMatchingPattern, -1)] as Value<?, ?>[]

        when:
        def resultMatches = stringValueTest.invokeMethod("matches", desc, matchingArgs)
        def resultNonMatches = stringValueTest.invokeMethod("matches", desc, nonMatchingArgs)
        
        then:
        println "Testing if string '${testString}' matches pattern '${regexPattern}'"
        println "Expected: true, Actual: ${resultMatches.concrete}"
        println "Testing if string '${testString}' matches pattern '${nonMatchingPattern}'"
        println "Expected: false, Actual: ${resultNonMatches.concrete}"
        
        resultMatches.concrete == true
        resultNonMatches.concrete == false
   }
}
