#!/bin/bash

# Exit on any error
set -o xtrace
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Usage check
if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <cp_dir> <harness_dirs..>"
    exit 1
fi

# Input arguments
CP_DIR="$1"
# Harness directory
shift
# HARNESS_DIRS -> "$@"

# build the jars dir for the static analysis server
STATIC_ANA_JARS="${CP_DIR}/out/harnesses/static-analysis-jars"
rm -rf ${STATIC_ANA_JARS}
mkdir -p ${STATIC_ANA_JARS}

# include all produced jar files
find "${CP_DIR}/out/harnesses/" -name '*.jar' | grep -v "static-analysis-jars" | while read jar; do
    cp ${jar} ${STATIC_ANA_JARS}
done

# run the server
${JAVA_WORK}/java_dict_generator/run-server.sh \
    ${JAVA_WORK}/java_dict_generator/target/dict-gen-1.0-jar-with-dependencies.jar \
    ${STATIC_ANA_JARS} \
    "$@"
