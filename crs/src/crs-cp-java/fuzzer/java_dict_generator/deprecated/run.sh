#!/bin/bash

set -e

[ $# -eq 1 ] || { echo "Usage: $0 <harness id: [1,12]>"; exit 1; }

#bash build.sh

SRC=../asc-challenge-002-jenkins-cp/src/
HARNESS_DIR=test
ID=$1

if [ $ID -eq 1 ]; then
	FUZZ_TARGET=id1
	HARNESS_CLASS=PipelineCommandUtilFuzzer_Fuzz
elif [ $ID -eq 2 ]; then
	# unsupported currently
	echo "Unsupported ID 2"
	exit 1
elif [ $ID -eq 3 ]; then
	FUZZ_TARGET=id3
	HARNESS_CLASS=ProxyConfigurationFuzzer_Fuzz
elif [ $ID -eq 4 ]; then
	FUZZ_TARGET=id4
	HARNESS_CLASS=CoverageProcessorFuzzer_Fuzz
elif [ $ID -eq 5 ]; then
	FUZZ_TARGET=id5
	HARNESS_CLASS=UserNameActionFuzzer_Fuzz
elif [ $ID -eq 6 ]; then
	FUZZ_TARGET=id6
	HARNESS_CLASS=StateMonitorFuzzer_Fuzz
elif [ $ID -eq 7 ]; then
	FUZZ_TARGET=id7
	HARNESS_CLASS=UserRemoteConfigFuzzer_Fuzz
elif [ $ID -eq 8 ]; then
	FUZZ_TARGET=id8
	HARNESS_CLASS=AuthActionFuzzer_Fuzz
elif [ $ID -eq 9 ]; then
	FUZZ_TARGET=id9
	HARNESS_CLASS=ApiFuzzer_Fuzz
elif [ $ID -eq 10 ]; then
	FUZZ_TARGET=id10
	HARNESS_CLASS=SecretMessageFuzzer_Fuzz
elif [ $ID -eq 11 ]; then
	FUZZ_TARGET=id11
	HARNESS_CLASS=AccessFilterFuzzer_Fuzz
elif [ $ID -eq 12 ]; then
	# unsupported currently
	echo "Unsupported ID 12"
	exit 1
else
	echo "Invalid ID"
	exit 1
fi

# Constructing classpath (copy from run_fuzzer.sh)
#
# include all produced jar files
CLASSPATH="${CLASSPATH}":$(find "${SRC}" -name "classpath" -type d -exec find {} -type f -name "*.jar" -printf "%p:" \;)
# include all produced class files
CLASSPATH="${CLASSPATH}":$(find "${SRC}" -name "build" -type d -printf "%p:")
# include the directory where the generated harnesses are stored
#CLASSPATH="${CLASSPATH}:${HARNESS_DIR}/${FUZZ_TARGET}/"
CLASSPATH="${CLASSPATH}:${HARNESS_DIR}/id1:${HARNESS_DIR}/id2:${HARNESS_DIR}/id3:${HARNESS_DIR}/id4:${HARNESS_DIR}/id5:${HARNESS_DIR}/id6:${HARNESS_DIR}/id7:${HARNESS_DIR}/id8:${HARNESS_DIR}/id9:${HARNESS_DIR}/id10:${HARNESS_DIR}/id11"
# include dependencies. These dirs don't exist. Looks like DARPA messed this up. We'll keep it for now.
#CLASSPATH="${CLASSPATH}:/root/.m2/repository/org/kohsuke/stapler/stapler/1822.v120278426e1c/stapler-1822.v120278426e1c.jar:${SRC}/javax.servlet-api-4.0.1.jar"
#echo "Classpath: ${CLASSPATH}"

# run dict generator
#java -jar target/dict-gen-1.0-jar-with-dependencies.jar \
#		cm \
#		-C ${CLASSPATH} \
#		-D ./${HARNESS_DIR}/id1,./${HARNESS_DIR}/id3 \
#		-c PipelineCommandUtilFuzzer_Fuzz,ProxyConfigurationFuzzer_Fuzz\
#		-m fuzzerTestOneInput,fuzzerTestOneInput \
#		-o ./${HARNESS_DIR}/id1/fuzz.dict,./${HARNESS_DIR}/id3/fuzz.dict
#
##		-D ./${HARNESS_DIR}/${FUZZ_TARGET} \
##		-D ./${HARNESS_DIR} \
##		-c ${HARNESS_CLASS} \
##		-o ./${HARNESS_DIR}/${FUZZ_TARGET}/fuzz.dict

#java -jar target/dict-gen-1.0-jar-with-dependencies.jar \
#		ps \
#		-C ${CLASSPATH} \
#		-D ./${HARNESS_DIR}

java -jar target/dict-gen-1.0-jar-with-dependencies.jar \
		dep \
		-C ${CLASSPATH} \
		-D ./aaa \
		-c PipelineCommandUtilPovRunner_Wrapper \
		-m fuzzerTestOneInput \
		-o stuck.json

#		-C ./aaa \
#		-C ${CLASSPATH} \
#		-C ./dump-classes \
#		-D ./dump-classes \

rm -rf sootOutput

#echo
#echo ------- RESULT -------
#echo

#cat ./${HARNESS_DIR}/${FUZZ_TARGET}/fuzz.dict
