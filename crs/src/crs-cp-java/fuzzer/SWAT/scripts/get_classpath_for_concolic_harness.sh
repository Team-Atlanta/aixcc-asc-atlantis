#!/bin/bash

# Exit on any error
set -o xtrace
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Usage check
#if ! [[ $# -eq 4 ]]; then
#    echo "Usage: $0 <cp_dir> <harness_dir> <fuzz_target_class> <mode>"
#    exit 1
#fi

JAZZER_PATH="${JAZZER_PATH:=/classpath/jazzer}"


# Input arguments
CP_DIR="$1"
# Harness directory
HARNESS_DIR="$2"
FUZZ_TARGET="$3"
MODE="$4"
HARNESS_ID="$5"

# the soot callgraph breaks in current generated harness (perhaps caused by defining two classes in one java file? TODO: debug this) 
if  [[ ${MODE} == "proto" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g'`
elif [[ ${MODE} == "naive" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_NaiveWrapper$//g'`
elif [[ ${MODE} == "concolic" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Concolic$//g'`
else
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g' | sed 's/_NaiveWrapper$//g'`
fi

PROJECT_YAML="${CP_DIR}/project.yaml"

BINARY_PATH=$(yq eval ".harnesses.${HARNESS_ID}.binary" "$PROJECT_YAML")

CHILD_FOLDER=$(dirname "$BINARY_PATH" | awk -F'/' '{print $NF}')

HARNESS_NUMBER=$CHILD_FOLDER




# Constructing classpath of for analyzing cp jar/class files
# 1. include all produced jar files
ANA_CLASSPATH=$(find $CP_DIR/out/harnesses/${HARNESS_NUMBER} -name '*.jar' -printf '%p:' | sed 's/:$//')
# 3. include the directory where the generated harnesses are stored
ANA_CLASSPATH="${ANA_CLASSPATH}:${HARNESS_DIR}/${FUZZ_TARGET}/"
# echo "Classpath for soot-based analysis: ${ANA_CLASSPATH}"

# Harness compile classpath
COMP_CLASSPATH="${ANA_CLASSPATH}"
# 4. include SootUp and dependencies
for jar in $(find /classpath/jazzer -name 'sootup*.jar'); do
    COMP_CLASSPATH="${COMP_CLASSPATH}:${jar}"
done
COMP_CLASSPATH="${COMP_CLASSPATH}":/classpath/jazzer/sootup-dependencies.jar
# 5. include our own jazzer
COMP_CLASSPATH="${COMP_CLASSPATH}":/classpath/jazzer/\*
# 6. add protobuf jar and proto files (generated) to the classpath
if [[ ${MODE} == "proto" ]]; then
    COMP_CLASSPATH="${COMP_CLASSPATH}:/protobuf/jar/protobuf-java-3.25.3.jar:${HARNESS_DIR}/${FUZZ_TARGET}/proto"
fi

# Detect the classes to be instrumented
# First, include every file in $HARNESS_DIR/$FUZZ_TARGET/ in the instrumentation
INSTRUMENTATION_INCLUDES="$(find "${HARNESS_DIR}/${FUZZ_TARGET}" -name "*.class" -printf "%f:" | sed 's/\.class//g')"
# Second, include all classes in the jenkins package
INSTRUMENTATION_INCLUDES="${INSTRUMENTATION_INCLUDES}":'jenkins.**:hudson.**:org.jenkinsci.**:com.cloudbees.**:io.jenkins.**:io.jenkins.blueocean.**:io.jenkins.plugins.**:io.jenkins.jenkinsfile'
# TODO: Set the instrumentation_includes argument based on the target (jenkins-independent for now)

COMP_CLASSPATH="${COMP_CLASSPATH}:${JAVA_WORK}/SWAT/binary-argument-loader/build/libs/binary-argument-loader.jar"
echo $COMP_CLASSPATH
