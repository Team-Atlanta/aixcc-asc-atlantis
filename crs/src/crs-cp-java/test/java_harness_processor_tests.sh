#!/usr/bin/env bash
CP_DIR=$AIXCC_CRS_SCRATCH_SPACE/java/jenkins
HARNESS_DIR=$AIXCC_CRS_SCRATCH_SPACE/java/harnesses/jenkins
SRC=$CP_DIR/src

set -e
FUZZ_FILES=$(find $HARNESS_DIR| grep "_Fuzz\.java$")
FILE_COUNT=$(echo "$FUZZ_FILES" | wc -l)

if [ $FILE_COUNT -eq 13 ]; then
    echo "Java harness processor test passed"
else
    echo "$FILE_COUNT test files found in $AIXCC_CRS_SCRATCH_SPACE/jenkins/harnesses; Java harness processor failed"
    exit 1
fi

HARNESS_PROCESSOR=$JAVA_FUZZER_SRC/java_harness_processor
pushd $HARNESS_PROCESSOR
./run_test.sh $CP_DIR --test-compile
