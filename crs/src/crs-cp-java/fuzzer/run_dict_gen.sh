#!/bin/bash

# Exit on any error
set -o xtrace
set -e

# Usage check
# if ! [[ $# -eq 3 ]]; then
#     echo "Usage: $0 <harness_dir> <fuzz_target> <mode>"
#     exit 1
# fi

# Input arguments
HARNESS_DIR="$1"
FUZZ_TARGET="$2"
MODE="$3"
TARGET_METHOD="fuzzerTestOneInput"

if  [[ ${MODE} == "proto" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g'`
elif [[ ${MODE} == "jazzer" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_JazzerFuzz$//g' | sed 's/_CJazzerFuzz$//g'`
elif [[ ${MODE} == "naive" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_NaiveWrapper$//g'`
else
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g' | sed 's/_NaiveWrapper$//g' | sed 's/_JazzerFuzz$//g' | sed 's/_CJazzerFuzz$//g'`
fi

# Wait for server initialized (time cost depends on the size of the classpath, jenkins analysis usually cost 2-3min with 6-8GB memory)
python3 ${JAVA_WORK}/java_dict_generator/client.py ping --timeout -1 1>/dev/null 2>&1

echo "Generating dictionary for ${POVRUNNER}; DEV=${DEV}"
# Generate dictionary for the fuzz target

python3 ${JAVA_WORK}/java_dict_generator/client.py dict \
                --targetClass "${POVRUNNER}" \
                --targetMethod "${TARGET_METHOD}" \
                --outputDict "${HARNESS_DIR}/${POVRUNNER}.dict" 1>/dev/null 2>&1
