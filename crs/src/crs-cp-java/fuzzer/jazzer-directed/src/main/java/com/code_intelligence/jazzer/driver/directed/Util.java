package com.code_intelligence.jazzer.driver.directed;

import com.google.common.collect.ImmutableSet;
import com.google.common.reflect.ClassPath;

import java.io.IOException;
import java.lang.management.ClassLoadingMXBean;
import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Util {

    public static ImmutableSet<ClassPath.ClassInfo> getAllLoadedClasses() {
        ClassPath classPath = null;
        try {
            classPath = ClassPath.from(Util.class.getClassLoader());
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return classPath.getAllClasses();
    }

    public static String guessFullClassName(String className) {
        // if className has '.' or starts with lower case letter, return unchanged className
        if (className.contains(".") || Character.isLowerCase(className.charAt(0))) {
            return className;
        }

        // Check the mapping
        String mappedName = fullNameMapping.get(className);
        if (mappedName != null) {
            return mappedName;
        }

        // Go through all loaded classes; if one of them matches this className, return it's fqdn
        for (ClassPath.ClassInfo classInfo : getAllLoadedClasses()) {
            if (classInfo.getName().endsWith("." + className)) {
                return classInfo.getName();
            }
        }

        return className;
    }

    private static Map<String, String> fullNameMapping;

    static {
        fullNameMapping = new HashMap<>();

        // java.lang.*
        fullNameMapping.put("Boolean", "java.lang.Boolean");
        fullNameMapping.put("Byte", "java.lang.Byte");
        fullNameMapping.put("Character", "java.lang.Character");
        fullNameMapping.put("Character.Subset", "java.lang.Character.Subset");
        fullNameMapping.put("Character.UnicodeBlock", "java.lang.Character.UnicodeBlock");
        fullNameMapping.put("Class", "java.lang.Class");
        fullNameMapping.put("ClassLoader", "java.lang.ClassLoader");
        fullNameMapping.put("ClassValue", "java.lang.ClassValue");
        fullNameMapping.put("Compiler", "java.lang.Compiler");
        fullNameMapping.put("Double", "java.lang.Double");
        fullNameMapping.put("Enum", "java.lang.Enum");
        fullNameMapping.put("Float", "java.lang.Float");
        fullNameMapping.put("InheritableThreadLocal", "java.lang.InheritableThreadLocal");
        fullNameMapping.put("Integer", "java.lang.Integer");
        fullNameMapping.put("Long", "java.lang.Long");
        fullNameMapping.put("Math", "java.lang.Math");
        fullNameMapping.put("Number", "java.lang.Number");
        fullNameMapping.put("Object", "java.lang.Object");
        fullNameMapping.put("Package", "java.lang.Package");
        fullNameMapping.put("Process", "java.lang.Process");
        fullNameMapping.put("ProcessBuilder", "java.lang.ProcessBuilder");
        fullNameMapping.put("ProcessBuilder.Redirect", "java.lang.ProcessBuilder.Redirect");
        fullNameMapping.put("Runtime", "java.lang.Runtime");
        fullNameMapping.put("RuntimePermission", "java.lang.RuntimePermission");
        fullNameMapping.put("SecurityManager", "java.lang.SecurityManager");
        fullNameMapping.put("Short", "java.lang.Short");
        fullNameMapping.put("StackTraceElement", "java.lang.StackTraceElement");
        fullNameMapping.put("StrictMath", "java.lang.StrictMath");
        fullNameMapping.put("String", "java.lang.String");
        fullNameMapping.put("StringBuffer", "java.lang.StringBuffer");
        fullNameMapping.put("StringBuilder", "java.lang.StringBuilder");
        fullNameMapping.put("System", "java.lang.System");
        fullNameMapping.put("Thread", "java.lang.Thread");
        fullNameMapping.put("ThreadGroup", "java.lang.ThreadGroup");
        fullNameMapping.put("ThreadLocal", "java.lang.ThreadLocal");
        fullNameMapping.put("Throwable", "java.lang.Throwable");
        fullNameMapping.put("Void", "java.lang.Void");

        // java.io.*
        fullNameMapping.put("BufferedInputStream", "java.io.BufferedInputStream");
        fullNameMapping.put("BufferedOutputStream", "java.io.BufferedOutputStream");
        fullNameMapping.put("BufferedReader", "java.io.BufferedReader");
        fullNameMapping.put("BufferedWriter", "java.io.BufferedWriter");
        fullNameMapping.put("ByteArrayInputStream", "java.io.ByteArrayInputStream");
        fullNameMapping.put("ByteArrayOutputStream", "java.io.ByteArrayOutputStream");
        fullNameMapping.put("CharArrayReader", "java.io.CharArrayReader");
        fullNameMapping.put("CharArrayWriter", "java.io.CharArrayWriter");
        fullNameMapping.put("Console", "java.io.Console");
        fullNameMapping.put("DataInputStream", "java.io.DataInputStream");
        fullNameMapping.put("DataOutputStream", "java.io.DataOutputStream");
        fullNameMapping.put("File", "java.io.File");
        fullNameMapping.put("FileDescriptor", "java.io.FileDescriptor");
        fullNameMapping.put("FileInputStream", "java.io.FileInputStream");
        fullNameMapping.put("FileOutputStream", "java.io.FileOutputStream");
        fullNameMapping.put("FilePermission", "java.io.FilePermission");
        fullNameMapping.put("FileReader", "java.io.FileReader");
        fullNameMapping.put("FileWriter", "java.io.FileWriter");
        fullNameMapping.put("FilterInputStream", "java.io.FilterInputStream");
        fullNameMapping.put("FilterOutputStream", "java.io.FilterOutputStream");
        fullNameMapping.put("FilterReader", "java.io.FilterReader");
        fullNameMapping.put("FilterWriter", "java.io.FilterWriter");
        fullNameMapping.put("InputStream", "java.io.InputStream");
        fullNameMapping.put("InputStreamReader", "java.io.InputStreamReader");
        fullNameMapping.put("LineNumberInputStream", "java.io.LineNumberInputStream");
        fullNameMapping.put("LineNumberReader", "java.io.LineNumberReader");
        fullNameMapping.put("ObjectInputStream", "java.io.ObjectInputStream");
        fullNameMapping.put("ObjectInputStream.GetField", "java.io.ObjectInputStream.GetField");
        fullNameMapping.put("ObjectOutputStream", "java.io.ObjectOutputStream");
        fullNameMapping.put("ObjectOutputStream.PutField", "java.io.ObjectOutputStream.PutField");
        fullNameMapping.put("ObjectStreamClass", "java.io.ObjectStreamClass");
        fullNameMapping.put("ObjectStreamField", "java.io.ObjectStreamField");
        fullNameMapping.put("OutputStream", "java.io.OutputStream");
        fullNameMapping.put("OutputStreamWriter", "java.io.OutputStreamWriter");
        fullNameMapping.put("PipedInputStream", "java.io.PipedInputStream");
        fullNameMapping.put("PipedOutputStream", "java.io.PipedOutputStream");
        fullNameMapping.put("PipedReader", "java.io.PipedReader");
        fullNameMapping.put("PipedWriter", "java.io.PipedWriter");
        fullNameMapping.put("PrintStream", "java.io.PrintStream");
        fullNameMapping.put("PrintWriter", "java.io.PrintWriter");
        fullNameMapping.put("PushbackInputStream", "java.io.PushbackInputStream");
        fullNameMapping.put("PushbackReader", "java.io.PushbackReader");
        fullNameMapping.put("RandomAccessFile", "java.io.RandomAccessFile");
        fullNameMapping.put("Reader", "java.io.Reader");
        fullNameMapping.put("SequenceInputStream", "java.io.SequenceInputStream");
        fullNameMapping.put("SerializablePermission", "java.io.SerializablePermission");
        fullNameMapping.put("StreamTokenizer", "java.io.StreamTokenizer");
        fullNameMapping.put("StringBufferInputStream", "java.io.StringBufferInputStream");
        fullNameMapping.put("StringReader", "java.io.StringReader");
        fullNameMapping.put("StringWriter", "java.io.StringWriter");
        fullNameMapping.put("Writer", "java.io.Writer");
    }
}
