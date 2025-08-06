# Introduction

Soot-based static analysis for generating dictionary to java fuzzing harnesses. It is expected to be built as standalone jar and used as a command line tool to the harness before fuzzing it.

# Occupied ports by default

- 25533 (Java side py4j port)
- 9505 (Python side web port)

# Server Mode Usage

Build the project:

```console
bash build.sh
```

Run the server:

```console
#
# venv wrapped bash script
bash run-server.sh <this-repo-jar> <cp-source-dir> <harness-dir>
#
# OR example command line by directly running server.py
python3 server.py -j target/dict-gen-1.0-jar-with-dependencies.jar -cp ../asc-challenge-002-jenkins-cp/ -d test/id1
```

Run client to test/use the server:

```console
# do query
python3 client.py ping
python3 client.py dict --targetClass=PipelineCommandUtilFuzzer --targetMethod=fuzzerTestOneInput --outputDict=./test/id1/fuzz.dict
python3 client.py rank --stuckBranchFile=./test/stuck.json --rankedBranchFile=./test/ranked-branch.json

# do test
python3 client.py test 
```

# Standalone Jar Usage

Compile as standalone jar:

```console
mvn clean compile assembly:single
```

It will be compiled as a standalone jar as `target/dict-gen-1.0-jar-with-dependencies.jar`.

Cmdline arguments:

```console
$ java -jar target/dict-gen-1.0-jar-with-dependencies.jar -h

Usage: java-static-analyzer [options] [command] [command options]
  Options:
    -h, --help
      Help/Usage
  Commands:
    dict-gen(dict)      null
      Usage: dict-gen(dict) [options]
        Options:
        * -C, --classpath
            classpath arguments of soot, the jar dependencies for analyzing
            the target harness
          -h, --help
            Help/Usage
          -o, --output-dicts
            filenames of the output dicts
        * -D, --processdirs
            processdir argument of soot, directories of the target harnesses
          -c, --target-classes
            class that entry function belongs to
          -m, --target-methods
            entry function that the dict extracts from

    branch-rank(rank)      null
      Usage: branch-rank(rank) [options]
        Options:
        * -C, --classpath
            classpath arguments of soot, the jar dependencies for analyzing
            the target harness
          -h, --help
            Help/Usage
        * -D, --processdirs
            processdir argument of soot, directories of the target harnesses
        * -o, --ranked-branch-file
            output file of the ranked branches
        * -i, --stuck-branch-file
            input file of the stuck branches

    stuck-branch(stuck)      null
      Usage: stuck-branch(stuck) [options]
        Options:
        * -C, --classpath
            classpath arguments of soot, the jar dependencies for analyzing
            the target harness
        * -i, --edgeID-file
            input file of the edge IDs
          -h, --help
            Help/Usage
        * -D, --processdirs
            processdir argument of soot, directories of the target harnesses
        * -o, --stuck-branches-files
            output file of the stuck branches

    server(srv)      null
      Usage: server(srv) [options]
        Options:
          -h, --help
            Help/Usage
```

# Example (DEPREACTED)

Execute `bash run.sh [id]` to get a result for harness in id 1-12. The `../asc-challenge-002-jenkins-cp/src/` must exist.

Inside the `run.sh`, it merely compile & setup cmdline arguments of the jar.

```console
...
java -jar target/dict-gen-1.0-jar-with-dependencies.jar \
        dict-gen \
		-C ${CLASSPATH} \
		-D ./${HARNESS_DIR}/${FUZZ_TARGET} \
		-c PipelineCommandUtilFuzzer_Fuzz \
		-m fuzzerTestOneInput \
		-o test/test.dict
...
```

Result dict of harness 1:

```console
str_1="workspace"
str_2="breakin the law" # this is what we want
str_3="RunScripts"
str_4="/resources/TBD"
str_5="login"
str_6="error"
str_7="INVALID"
str_8="Read"
str_9="slave"
str_10="logout"
str_11="view"
str_12="listView"
str_13="oops"
str_14="accessDenied"
str_15="jenkins"
str_16="ERROR"
str_17="\|"
str_18="SUCCESS"
str_19="Error: empty result"
str_20="adjuncts"
str_21="SystemRead"
str_22="securityRealm"
str_23="Referer"
str_24="Manage"
str_25="signup"
str_26="jdk"
str_27="x-evil-backdoor" # this is what we want
str_28="enabledAgentProtocol"
str_29="loginError"
str_30="anonymous"
```

Result dict of harness 4:
```console
str_1="coverage-report" # this is what we want
```

Result dict of harness 6:
```console
str_1="nimda"
str_2="password" # this is what we want
str_3="application/json"
str_4="^[a-zA-Z]+$"
str_5="UTF-8"
str_6="name" # this is what we want
str_7="admin" # this is what we want
str_8="STABLE"
```

More dict results of the harnesses can be found at `test/id*/fuzz.dict`.

# NOTE

The analysis can take 6 - 8 GB memory at most in my testing. This is because there are too many involved jars set in classpath for cp-jenkins harnesses.

# TODO

- Removing noises in dict, LLM is a good direction (low token cost in dict gen & good at handling corner cases)
- Can irrelevant jar be filtered to boost analysis?
