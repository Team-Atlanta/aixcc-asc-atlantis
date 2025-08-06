#!/bin/bash

# Exit on any error
set -o xtrace
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Usage check
# if ! [[ $# -eq 4 ]]; then
#     echo "Usage: $0 <cp_dir> <harness_dir> <fuzz_target_class> <mode>"
#     exit 1
# fi

JAZZER_PATH="${JAZZER_PATH:=/classpath/jazzer}"


# Input arguments
CP_DIR="$1"
# Harness directory
HARNESS_DIR="$2"
FUZZ_TARGET="$3"
MODE="$4"
HARNESS_ID="$5"

if  [[ ${MODE} == "proto" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g'`
elif [[ ${MODE} == "jazzer" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_JazzerFuzz$//g' | sed 's/_CJazzerFuzz$//g'`
elif [[ ${MODE} == "naive" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_NaiveWrapper$//g'`
elif [[ ${MODE} == "concolic" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Concolic$//g'`
else
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g' | sed 's/_NaiveWrapper$//g' | sed 's/_JazzerFuzz$//g' | sed 's/_CJazzerFuzz$//g'`
fi

PROJECT_YAML="${CP_DIR}/project.yaml"

BINARY_PATH=$(yq eval ".harnesses.${HARNESS_ID}.binary" "$PROJECT_YAML")

CHILD_FOLDER=$(dirname "$BINARY_PATH" | awk -F'/' '{print $NF}')

HARNESS_NUMBER=$CHILD_FOLDER

# Create harness work directory
rm -rf "${HARNESS_DIR}/${FUZZ_TARGET}" && mkdir -p "${HARNESS_DIR}/${FUZZ_TARGET}"

# Constructing classpath of for analyzing cp jar/class files
# 1. include all produced jar files
ANA_CLASSPATH=$(find $CP_DIR/out/harnesses/${HARNESS_NUMBER} -name '*.jar' -printf '%p:' | sed 's/:$//')
# 3. include the directory where the generated harnesses are stored
ANA_CLASSPATH="${ANA_CLASSPATH}:${HARNESS_DIR}/${FUZZ_TARGET}/"
# echo "Classpath for soot-based analysis: ${ANA_CLASSPATH}"

# Harness compile classpath
COMP_CLASSPATH="${ANA_CLASSPATH}"
# 4. include SootUp and dependencies
for jar in $(find ${JAZZER_PATH} -name 'sootup*.jar'); do
    COMP_CLASSPATH="${COMP_CLASSPATH}:${jar}"
done
COMP_CLASSPATH="${COMP_CLASSPATH}":${JAZZER_PATH}/sootup-dependencies.jar
# 5. include our own jazzer
COMP_CLASSPATH="${COMP_CLASSPATH}":${JAZZER_PATH}/\*
# 6. add protobuf jar and proto files (generated) to the classpath
if [[ ${MODE} == "proto" ]]; then
    COMP_CLASSPATH="${COMP_CLASSPATH}:/protobuf/jar/protobuf-java-3.25.3.jar:${HARNESS_DIR}/proto/${FUZZ_TARGET}"
fi
# echo "Harness compile classpath: ${COMP_CLASSPATH}"

# Compile the harness
if [[ ${MODE} == "proto" ]]; then
    echo "Compiling harness with proto"
    PROTO_OUT_DIR="${HARNESS_DIR}/proto/${FUZZ_TARGET}"
    rm -rf ${PROTO_OUT_DIR}
    mkdir -p ${PROTO_OUT_DIR}
    cp "${HARNESS_DIR}/${FUZZ_TARGET}.proto" ${PROTO_OUT_DIR}/HarnessInput.proto
    protoc --proto_path=${PROTO_OUT_DIR} --java_out=${PROTO_OUT_DIR} "${PROTO_OUT_DIR}/HarnessInput.proto"
elif [[ ${MODE} == "jazzer" ]]; then
    echo "Compiling harness with jazzer"
elif [[ ${MODE} == "naive" ]]; then
    echo "Compiling harness with wrapper"
elif [[ ${MODE} == "concolic" ]]; then
    echo "Compiling harness for concolic"
    COMP_CLASSPATH="${COMP_CLASSPATH}:${JAVA_WORK}/SWAT/binary-argument-loader/build/libs/binary-argument-loader.jar"
else
    echo "Compiling harness without mode"
fi

javac -d "${HARNESS_DIR}/${FUZZ_TARGET}" -cp "${COMP_CLASSPATH}" "${HARNESS_DIR}/${FUZZ_TARGET}.java"

# concolic does not use BlobGenerator
# mode == "proto" or mode == "jazzer"
if [[ ${MODE} == "proto" ]]; then
    javac -d "${HARNESS_DIR}/${FUZZ_TARGET}" -cp "${COMP_CLASSPATH}" "${HARNESS_DIR}/${POVRUNNER}_BlobGenerator.java"
elif [[ ${MODE} == "jazzer" ]]; then
    javac -d "${HARNESS_DIR}/${FUZZ_TARGET}" -cp "${COMP_CLASSPATH}" "${HARNESS_DIR}/${POVRUNNER}_JazzerBlobGenerator.java"
fi
