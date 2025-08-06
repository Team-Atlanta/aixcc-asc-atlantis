package com.code_intelligence.jazzer.sanitizers;

import com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical;
import com.code_intelligence.jazzer.api.HookType;
import com.code_intelligence.jazzer.api.Jazzer;
import com.code_intelligence.jazzer.api.MethodHook;

import java.io.File;
import java.lang.invoke.MethodHandle;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * This tests for a file read or write of a specific file name.
 *
 * When modifying this class, make sure to modify {@link FileSystemTraversal} as well
 */
public class FileReadWrite {
    public static final String ENV_KEY = "JAZZER_FILE_READ_WRITE";
    public static final String DEFAULT_SENTINEL = "jazzer";
    public static final String SENTINEL =
            (System.getenv(ENV_KEY) == null || System.getenv(ENV_KEY).trim().length() == 0) ?
                    DEFAULT_SENTINEL : System.getenv(ENV_KEY);

    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "newByteChannel"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "newBufferedReader"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "newBufferedWriter"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "readString"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "newBufferedReader"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "readAllBytes"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "readAllLines"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "readSymbolicLink"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "write"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "writeString"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "newInputStream"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "newOutputStream"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.channels.FileChannel",
            targetMethod = "open"
    )
    public static void processPathHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {
            Object argObj = arguments[0];
            if (argObj instanceof Path) {
                if (argObj instanceof Path) {
                    maybeReport((Path)argObj, hookId);
                }
            }
        }
    }
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "copy"
    )
    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.nio.file.Files",
            targetMethod = "move"
    )
    public static void copyMvHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 1) {
            Object argObj = arguments[1];
            if (argObj instanceof Path) {
                maybeReport((Path)argObj, hookId);
            }
        }
    }
    

    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.io.FileReader",
            targetMethod = "<init>"
    )
    public static void fileReaderHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {

            Object argObj = arguments[0];
            if (argObj instanceof String) {
                maybeReport((String)argObj, hookId);
            } else if (argObj instanceof File) {
                maybeReport((File)argObj, hookId);
            }
        }
    }

    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.io.FileWriter",
            targetMethod = "<init>"
    )
    public static void fileWriterHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {

            Object argObj = arguments[0];
            if (argObj instanceof String) {
                maybeReport((String)argObj, hookId);
            } else if (argObj instanceof File) {
                maybeReport((File)argObj, hookId);
            }
        }
    }



    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.io.FileInputStream",
            targetMethod = "<init>"
    )
    public static void fileInputStreamHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {

            Object argObj = arguments[0];
            if (argObj instanceof String) {
                maybeReport((String)argObj, hookId);
            } else if (argObj instanceof File) {
                maybeReport((File)argObj, hookId);
            }
        }
    }

    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.io.FileOutputStream",
            targetMethod = "<init>"
    )
    public static void processFileOutputStartHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {
            Object argObj = arguments[0];
            if (argObj instanceof File) {
                if (argObj instanceof String) {
                    maybeReport((String)argObj, hookId);
                } else if (argObj instanceof File) {
                    maybeReport((File)argObj, hookId);
                }
            }
        }
    }

    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.util.Scanner",
            targetMethod = "<init>"
    )
    public static void scannerHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {

            Object argObj = arguments[0];
            if (argObj instanceof String) {
                maybeReport((String)argObj, hookId);
            } else if (argObj instanceof Path) {
                maybeReport((Path)argObj, hookId);
            } else if (argObj instanceof File) {
                maybeReport((File)argObj, hookId);
            }
        }
    }

    @MethodHook(
            type = HookType.BEFORE,
            targetClassName = "java.io.FileOutputStream",
            targetMethod = "<init>"
    )
    public static void fileOutputStreamHook(
            MethodHandle method, Object thisObject, Object[] arguments, int hookId) {
        Jazzer.recordReachedSanitizer("FileReadWrite", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {

            Object argObj = arguments[0];
            if (argObj instanceof File) {
                maybeReport((File)argObj, hookId);
            } else if (argObj instanceof String) {
                maybeReport((String)argObj, hookId);
            }
        }
    }

    private static void maybeReport(String s, int hookId) {
        try {
            maybeReport(Paths.get(s), hookId);
        } catch (InvalidPathException e) {
            maybeReport(new File(s), hookId);
        }
    }

    private static void maybeReport(File f, int hookId) {
        try {
            maybeReport(f.toPath(), hookId);
        } catch (InvalidPathException e) {
            if (f.getName().equals(SENTINEL)) {
                Jazzer.reportFindingFromHook(
                        new FuzzerSecurityIssueCritical("File read/write hook path: " + f ));
            }
        }
    }
    
    private static void maybeReport(Path p, int hookId) {
        String filename = p.getFileName().toString();
        Jazzer.guideTowardsContainment(filename, SENTINEL, hookId);

        if (filename.equals(SENTINEL)) {
            Jazzer.reportFindingFromHook(
                    new FuzzerSecurityIssueCritical("File read/write hook path: " + p));
        }
    }


}

