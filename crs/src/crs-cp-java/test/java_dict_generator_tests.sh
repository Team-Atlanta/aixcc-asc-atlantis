#!/usr/bin/env bash

set -e

HELLOWORLD_SRC="${JAVA_FUZZER_SRC}/java_dict_generator/test/helloworld"
TMP_DIR="/tmp/java_dict_generator_tests"

rm -rf ${TMP_DIR}
mkdir -p ${TMP_DIR}
cd ${TMP_DIR}
cp -r ${HELLOWORLD_SRC} .

java -jar /classpath/java_dict_generator_with_dependencies.jar \
			-C "" \
			-D ${TMP_DIR}/helloworld\
			-c HelloWorld \
			-m main \
			-o fuzz.dict

# test failed
if [ ! -f ${TMP_DIR}/fuzz.dict ]
then
        echo "Failed to generate dict file" && exit 1
fi

cd -
rm -rf ${TMP_DIR}
