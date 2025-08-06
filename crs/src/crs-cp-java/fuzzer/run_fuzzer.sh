#!/bin/bash

# Exit on any error
set -o xtrace
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Usage check
# if ! [[ $# -eq 5 || $# -eq 6 ]]; then
#     echo "Usage: $0 <cp_dir> <harness_dir> <fuzz_target_class> <mode> <repo_list> [--disable_directed_fuzzing]"
#     exit 1
# fi

JAZZER_PATH="${JAZZER_PATH:=/classpath/jazzer}"

if [ "$JAZZER_PATH" = "/classpath/jazzer_directed" ]; then
  IS_DIRECTED_JAZZER=true
else
  IS_DIRECTED_JAZZER=false
fi

# Input arguments
CP_DIR="$1"
# Harness directory
HARNESS_DIR="$2"
FUZZ_TARGET="$3"
MODE="$4"
REPO_LIST="$5"
HARNESS_ID="$6"
CORE_PER_HARNESS="$7"
DISABLE_DIRECTED_FUZZING="$8"

N_KEEP_GOING=1000
EXECUTION_TIMEOUT=1200 # Wait for 5 minutes before killing the harness

# the soot callgraph breaks in current generated harness (perhaps caused by defining two classes in one java file? TODO: debug this) 
if  [[ ${MODE} == "proto" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g'`
elif [[ ${MODE} == "jazzer" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_JazzerFuzz$//g' | sed 's/_CJazzerFuzz$//g'`
elif [[ ${MODE} == "naive" ]]; then
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_NaiveWrapper$//g'`
else
    POVRUNNER=`echo ${FUZZ_TARGET} | sed 's/_Fuzz$//g' | sed 's/_NaiveWrapper$//g' | sed 's/_JazzerFuzz$//g' | sed 's/_CJazzerFuzz$//g'`
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

# Detect the classes to be instrumented
# First, include every file in $HARNESS_DIR/$FUZZ_TARGET/ in the instrumentation
INSTRUMENTATION_INCLUDES="$(find "${HARNESS_DIR}/${FUZZ_TARGET}" -name "*.class" -printf "%f:" | sed 's/\.class//g')"
# Second, include all classes in the jenkins package
#INSTRUMENTATION_INCLUDES="${INSTRUMENTATION_INCLUDES}":'jenkins.**:hudson.**:org.jenkinsci.**:com.cloudbees.**:io.jenkins.**:io.jenkins.blueocean.**:io.jenkins.plugins.**:io.jenkins.jenkinsfile'
INSTRUMENTATION_INCLUDES="${INSTRUMENTATION_INCLUDES}":'aixcc.**:antlr.**:com.sonyericsson.jenkins.**:executable:hudson.**:io.jenkins.**:jenkins.**:lib.form.**:lib.hudson.**:lib.layout.**:org.acegisecurity.**:org.jenkins.**:org.kohsuke.**:org.springframework.dao.**:scripts.**:org.jenkinsci.**:com.cloudbees.**'
# TODO: Set the instrumentation_includes argument based on the target (jenkins-independent for now)

# Explicitly enable command tracing
set -o xtrace

# Setup directories for Jazzer artifacts, reproducer, and corpus
WORK_DIR=`realpath "${HARNESS_DIR}"`/fuzz/${FUZZ_TARGET}
ARTIFACT_DIR=${WORK_DIR}/artifacts
REPRODUCER_DIR=${WORK_DIR}/reproducer
CORPUS_DIR=${WORK_DIR}/corpus_dir
TARGETS_FILE=${WORK_DIR}/targets_file.txt
INSTRUMENTED_CLASSES_DIR=${WORK_DIR}/instrumented_classes
SCORES_DIR=${WORK_DIR}/scores_dir


# the proto harness saves input in proto serailized format, we transform it after fuzzing
if  [[ ${MODE} == "proto" ]]; then
  ORI_CORPUS_DIR=${CORPUS_DIR}
  CORPUS_DIR=${ORI_CORPUS_DIR}"_proto_format"
  ORI_ARTIFACT_DIR=${ARTIFACT_DIR}
  ARTIFACT_DIR=${ORI_ARTIFACT_DIR}"_proto_format"

# NOTE: save an abs path to the proto_input_transform.sh script for convient use in anywhere
# TODO: currently this script can be called (e.g., os.system(SCRIPT_PATH)) in any working directory without any arg to do the transformation
#       perhaps we need a parameterized one in the future
  mkdir -p ${HARNESS_DIR}/fuzz/${FUZZ_TARGET}
  cat > ${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/proto_input_transform.sh <<EOF
mkdir -p ${ORI_CORPUS_DIR}
ls ${CORPUS_DIR} | while read f
do 
  /usr/lib/jvm/java-17-openjdk-amd64/bin/java -cp ${COMP_CLASSPATH} LocalBlobGenerator ${CORPUS_DIR}/\${f} ${ORI_CORPUS_DIR}/\${f} >/dev/null 2>&1 || echo "skip invalid proto seed ${CORPUS_DIR}/\${f}"
done

mkdir -p ${ORI_ARTIFACT_DIR}
ls ${ARTIFACT_DIR} | grep "crash-" | while read f
do 
  /usr/lib/jvm/java-17-openjdk-amd64/bin/java -cp ${COMP_CLASSPATH} LocalBlobGenerator ${ARTIFACT_DIR}/\${f} ${ORI_ARTIFACT_DIR}/\${f} >/dev/null 2>&1 || echo "skip invalid proto seed ${ARTIFACT_DIR}/\${f}"
done
EOF
  chmod +x ${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/proto_input_transform.sh

elif [[ ${MODE} == "jazzer" ]]; then
  # the jazzer harness saves input in serialized format, we transform it after fuzzing
  ORI_CORPUS_DIR=${CORPUS_DIR}
  CORPUS_DIR=${ORI_CORPUS_DIR}"_jazzer_format"
  ORI_ARTIFACT_DIR=${ARTIFACT_DIR}
  ARTIFACT_DIR=${ORI_ARTIFACT_DIR}"_jazzer_format"

  mkdir -p ${HARNESS_DIR}/fuzz/${FUZZ_TARGET}
  cat > ${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/jazzer_input_transform.sh <<EOF
mkdir -p ${ORI_CORPUS_DIR}
ls ${CORPUS_DIR} | while read f
do 
  /usr/lib/jvm/java-17-openjdk-amd64/bin/java -cp ${COMP_CLASSPATH} LocalBlobGenerator ${CORPUS_DIR}/\${f} ${ORI_CORPUS_DIR}/\${f} >/dev/null 2>&1 || echo "skip invalid jazzer seed ${CORPUS_DIR}/\${f}"
done

mkdir -p ${ORI_ARTIFACT_DIR}
ls ${ARTIFACT_DIR} | grep "crash-" | while read f
do 
  /usr/lib/jvm/java-17-openjdk-amd64/bin/java -cp ${COMP_CLASSPATH} LocalBlobGenerator ${ARTIFACT_DIR}/\${f} ${ORI_ARTIFACT_DIR}/\${f} >/dev/null 2>&1 || echo "skip invalid jazzer seed ${ARTIFACT_DIR}/\${f}"
done
EOF
  chmod +x ${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/jazzer_input_transform.sh

fi

mkdir -p "${WORK_DIR}"
mkdir -p "${ARTIFACT_DIR}"
mkdir -p "${REPRODUCER_DIR}"
mkdir -p "${CORPUS_DIR}"
mkdir -p "${INSTRUMENTED_CLASSES_DIR}"
mkdir -p "${SCORES_DIR}"

# TODO: Replace this with a more meaningful seed (e.g., Joonun's outcome)
if [[ -d "${JAVA_CRS_SRC}/corpus" ]]; then
  echo "Copying seed corpus"
  cp ${JAVA_CRS_SRC}/corpus/* "${CORPUS_DIR}"
else
  echo "AAAA" > "${CORPUS_DIR}/init_seed"
fi

if [ "${IS_DIRECTED_JAZZER}" = true ]; then

if [[ "${DISABLE_DIRECTED_FUZZING}" == "--disable_directed_fuzzing" ]]; then
    directed_fuzzing_args="--dump_classes_dir=${INSTRUMENTED_CLASSES_DIR} -target_distance_dir=${SCORES_DIR}"
else
    # Generate the targets file
    FUZZED_HARNESS="${HARNESS_DIR}/${FUZZ_TARGET}.java"
    timeout 5m ${SCRIPT_DIR}/jazzer_adapter.sh ${FUZZED_HARNESS} ${TARGETS_FILE} ${REPO_LIST}

    if [[ ! -f ${TARGETS_FILE} ]]; then
      echo "Error: Could not generate targets file"
      directed_fuzzing_args="--dump_classes_dir=${INSTRUMENTED_CLASSES_DIR} -target_distance_dir=${SCORES_DIR}"
    else
      echo "Targets file generated successfully"
      directed_fuzzing_args="--directed_fuzzing_targets=${TARGETS_FILE} --dump_classes_dir=${INSTRUMENTED_CLASSES_DIR} -target_distance_dir=${SCORES_DIR}"
    fi
fi
else
  directed_fuzzing_args=""
fi 

if [[ ${MODE} == "jazzer" ]]; then
  echo "Dumping fuzzer cfgs for introspection"
  cat > "${WORK_DIR}/fuzzer_cfg.txt" <<EOF
  work_dir = ${WORK_DIR}
  classpath = ${COMP_CLASSPATH}
  instrumentation_includes = ${INSTRUMENTATION_INCLUDES}
  harness = ${FUZZ_TARGET}
  dict_file = ${HARNESS_DIR}/${POVRUNNER}.dict
  corpus_dir = ${CORPUS_DIR}
  total_fuzzing_time = ${TOTAL_FUZZING_TIME}
  keep_going = ${N_KEEP_GOING}
EOF

  # TODO: confirm the log file path (need libfuzzer stderr log & the log format for introspection)
  # Running introspected fuzzing in background
  python3 ${JAVA_WORK}/java_introspected_fuzzing/main.py \
          ${WORK_DIR}/fuzzer_cfg.txt \
          ${WORK_DIR}/stderr \
          ${WORK_DIR}/introspected_fuzz.log &
fi

export JAZZER_FUZZ=1
# write a placeholder line to dict in case the dict has not been generated
if [[ ! -f ${HARNESS_DIR}/${POVRUNNER}.dict ]]; then
  echo '# PLACEHOLDER' >> ${HARNESS_DIR}/${POVRUNNER}.dict
fi

fork_args=""
if [[ "${CORE_PER_HARNESS}" -gt 1 ]]; then
  fork_args="-jobs=${CORE_PER_HARNESS}"
fi

MAX_GC_THREAD=2
MAX_GC1_THREAD=1
MAX_THREAD=3

if [[ "${CORE_PER_HARNESS}" -gt 6 ]]; then
  MAX_GC_THREAD=$((CORE_PER_HARNESS / 5))
  if [[ "$MAX_GC_THREAD" -lt 2 ]]; then
    MAX_GC_THREAD=2
  fi

  MAX_GC1_THREAD=$((MAX_GC_THREAD / 3))
  if [[ "$MAX_GC1_THREAD" -lt 1 ]]; then
    MAX_GC1_THREAD=1
  fi

  MAX_THREAD=$((CORE_PER_HARNESS - MAX_GC_THREAD - MAX_GC1_THREAD))
  if [[ "$MAX_THREAD" -lt 3 ]]; then
    MAX_THREAD=3
  fi
fi

# Start Jazzer. Arguments with two dashes are for jazzer, and arguments with
# one dash are for libfuzzer (as well as the corpus directory).
# TODO: Increase the max_total_time argument
echo "Starting Jazzer"


timeout -s SIGKILL ${TOTAL_FUZZING_TIME}s stdbuf -e 0 -o 0 bash ${SCRIPT_DIR}/_run_fuzzer_timeout_stub.sh \
        --reproducer_path="${REPRODUCER_DIR}" \
        --agent_path=${JAZZER_PATH}/jazzer_standalone_deploy.jar \
        "--cp=${COMP_CLASSPATH}" \
        --target_class="${FUZZ_TARGET}" \
        "--instrumentation_excludes=org.apache.logging.**:com.fasterxml.**:org.apache.commons.**" \
        "--disabled_hooks=com.code_intelligence.jazzer.sanitizers.IntegerOverflow" \
        --jvm_args="-Djdk.attach.allowAttachSelf=true:-XX\:+StartAttachListener:-Xmx4g:-XX\:ParallelGCThreads=${MAX_GC_THREAD}:-XX\:ConcGCThreads=${MAX_GC1_THREAD}:-Djava.util.concurrent.ForkJoinPool.common.parallelism=${MAX_THREAD}" \
        --keep_going=${N_KEEP_GOING} \
        --experimental_mutator=1 \
        ${directed_fuzzing_args} \
        ${fork_args} \
        -use_value_profile=1 \
        -artifact_prefix="${ARTIFACT_DIR}/" \
        -reload=1 \
        -max_total_time=${TOTAL_FUZZING_TIME} \
        -dict=${HARNESS_DIR}/${POVRUNNER}.dict \
        -close_fd_mask=1 \
        -timeout=${EXECUTION_TIMEOUT} \
        "${CORPUS_DIR}"
        #-keep_seed=1 \
        #--instrumentation_includes="${INSTRUMENTATION_INCLUDES}" \

# post-processing to guarantee the corpus/artifact are aligned with other fuzz harnesses
if  [[ "${MODE}" == "proto" ]]; then
  if [[ -f "${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/proto_input_transform.sh" ]]; then
    bash "${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/proto_input_transform.sh"
  else
    echo "${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/proto_input_transform.sh not found when running in proto mode"
    exit 1
  fi
elif [[ "${MODE}" == "jazzer" ]]; then
  if [[ -f "${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/jazzer_input_transform.sh" ]]; then
    bash "${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/jazzer_input_transform.sh"
  else
    echo "${HARNESS_DIR}/fuzz/${FUZZ_TARGET}/jazzer_input_transform.sh not found when running in jazzer mode"
    exit 1
  fi
fi


ls -lh "${CORPUS_DIR}"
