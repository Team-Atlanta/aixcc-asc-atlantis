package com.code_intelligence.jazzer.sanitizers;

import com.code_intelligence.jazzer.api.FuzzerSecurityIssueCritical;
import com.code_intelligence.jazzer.api.HookType;
import com.code_intelligence.jazzer.api.Jazzer;
import com.code_intelligence.jazzer.api.MethodHook;

import java.io.IOException;
import java.io.File;
import java.lang.invoke.MethodHandle;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * This tests for a file read or write of a specific file name AND
 * whether that file is in an allowed directory or a descendant
 *
 * When modifying this class, make sure to modify {@link FileReadWrite} as well
 */
public class FileSystemTraversal {
    public static final String FILE_NAME_ENV_KEY = "JAZZER_FILE_SYSTEM_TRAVERSAL_FILE_NAME";
    public static final String ALLOWED_DIRS_KEY = "jazzer.fs_allowed_dirs";
    public static final String DEFAULT_SENTINEL = "jazzer-traversal";
    public static final String SENTINEL =
            (System.getenv(FILE_NAME_ENV_KEY) == null ||
                    System.getenv(FILE_NAME_ENV_KEY).trim().length() == 0) ?
                    DEFAULT_SENTINEL : System.getenv(FILE_NAME_ENV_KEY);

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

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
        Jazzer.recordReachedSanitizer("FileSystemTraversal", "xxx", "xxx", new String[]{SENTINEL});

        if (arguments.length > 0) {

            Object argObj = arguments[0];
            if (argObj instanceof File) {
                maybeReport((File)argObj, hookId);
            } else if (argObj instanceof String) {
                maybeReport((String)argObj, hookId);
            }
        }
    }

    private static void maybeReport(File f, int hookId) {
        try {
            maybeReport(f.toPath(), hookId);
        } catch (InvalidPathException e) {
            //TODO: give up -- for now
        }
    }

    private static void maybeReport(String s, int hookId) {
        try {
            maybeReport(Paths.get(s), hookId);
        } catch (InvalidPathException e) {
            maybeReport(new File(s), hookId);
        }
    }

    private static void maybeReport(Path p, int hookId) {
        String filename = p.getFileName().toString();
        Jazzer.guideTowardsContainment(filename, SENTINEL, hookId);

        if (filename.equals(SENTINEL) && ! isAllowed(p)) {
            Jazzer.reportFindingFromHook(
                    new FuzzerSecurityIssueCritical("File read/write hook path: " + p));
        }
    }

    private static boolean isAllowed(Path candidate) {
        String allowedDirString = System.getProperty(ALLOWED_DIRS_KEY);
        if (allowedDirString == null || allowedDirString.trim().length() == 0) {
            return true;
        }

        Path candidateNormalized = candidate.toAbsolutePath().normalize();
        for (String pString : allowedDirString.split(",")) {
            Path allowedNormalized = Paths.get(pString).toAbsolutePath().normalize();
            if (isSameFile(candidateNormalized, allowedNormalized)) {
                //has to be a descendant
                return false;
            }
            if (isDescendant(allowedNormalized, candidateNormalized)) {
                return true;
            }
        }
        return false;
    }

    //paths must be absolute and normalized before this test
    private static boolean isDescendant(Path ancestor, Path candidate) {

        Path candidateParent = candidate.getParent();
        if (candidateParent == null) {
            return false;
        }
        if (isSameFile(ancestor, candidateParent)) {
            return true;
        } else if (isDescendant(ancestor, candidateParent)) {
            return true;
        } else {
            return false;
        }
    }

    //paths must be absolute and normalized before this testl
    private static boolean isSameFile(Path ancestor, Path candidate) {
        try {
            return Files.isSameFile(ancestor, candidate);
        } catch (IOException e) {
            //isSameFile may try a file read, and that file will likely
            //not exist.
            return ancestor.equals(candidate);
        }
    }

}

