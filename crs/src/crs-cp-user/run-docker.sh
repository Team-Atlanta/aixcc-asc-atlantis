#!/bin/bash

set -euo pipefail


echo -e "\033[32m\n [!] For a clean workspace, please remove ./cp_root and ./crs_scratch manually \n\033[0m"

echo -e "\033[32m\n [!] To simulate the ASC env, please only add one CP in ./cp_root for each time \n\033[0m"


export BUILD_USERSPACE_CP=1 # for local testing, we always want this

export ENABLE_BUILTIN_LIBFUZZER=${ENABLE_BUILTIN_LIBFUZZER:-1}
export ENABLE_LIBAFL_LIBFUZZER=${ENABLE_LIBAFL_LIBFUZZER:-1}

PROFILE=development

ROOT=$(realpath $(dirname "$0"))
AIXCC_CP_ROOT=${AIXCC_CP_ROOT:-$ROOT/cp_root}
AIXCC_CRS_SCRATCH_SPACE=${AIXCC_CRS_SCRATCH_SPACE:-$ROOT/crs_scratch}

MOCK_CP="$AIXCC_CP_ROOT/mock-cp"
MAIN_COMMAND=${1:-run}
LATEST_ARVO=${LATEST_ARVO:-31124}


build_cps() {
  make cps/clean
  make cps

  mkdir -p $ROOT/crs_scratch
  rm -rf $ROOT/crc_scratch/*

  mkdir -p "$AIXCC_CP_ROOT"
  
  # Until benchmarks are done, disable
  # build_arvo

  for entry in `ls "$AIXCC_CP_ROOT"`
  do
    if ! [[ "$entry" =~ ^arvo- ]]; then
      (cd $AIXCC_CP_ROOT/$entry && git checkout -f . || exit -1)
    fi
    (cd $AIXCC_CP_ROOT/$entry && make cpsrc-prepare || exit -1)
    (cd $AIXCC_CP_ROOT/$entry && make docker-build || true)
    (cd $AIXCC_CP_ROOT/$entry && make docker-config-local || true)
  done
}


build_modules() {
    cd $ROOT
    pip3 install -r requirements-arvo.txt
    pip3 install -r requirements.txt

    # This is used as an imported module
    cd $ROOT/preprocessor
    pip3 install -r requirements.txt

    cd $ROOT/reverser
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip3 install -r requirements.txt

    cd $ROOT/reverser/static
    ./build.sh

    cd $ROOT/verifier
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip3 install -r requirements.txt

    cd $ROOT/commit-analyzer
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip3 install -r requirement.txt

    cd $ROOT
}


# test for a specific arvo CP
if [[ "$MAIN_COMMAND" == arvo-* ]]; then
  # copy and build arvo cp
  if [ ! -d "$AIXCC_CP_ROOT" ]; then
    # Create the directory
    mkdir -p "$AIXCC_CP_ROOT"
    echo "Directory $AIXCC_CP_ROOT created."
  fi

  if [ ! -d "$AIXCC_CRS_SCRATCH_SPACE" ]; then
    # Create the directory
    mkdir -p "$AIXCC_CRS_SCRATCH_SPACE"
    echo "Directory AIXCC_CRS_SCRATCH_SPACE created."
  fi

  if [ ! -d "${AIXCC_CRS_SCRATCH_SPACE}/arvo" ]; then
    git clone "git@github.com:Team-Atlanta/arvo.git" "${AIXCC_CRS_SCRATCH_SPACE}/arvo"
    git clone -b bic-check "git@github.com:Team-Atlanta/arvo2exemplar.git" "${AIXCC_CRS_SCRATCH_SPACE}/arvo2exemplar"
  fi

  cp -rf "${AIXCC_CRS_SCRATCH_SPACE}/arvo2exemplar/cp/${MAIN_COMMAND}" "${AIXCC_CP_ROOT}/${MAIN_COMMAND}"

  # we handle this in run.py
  pushd "${AIXCC_CRS_SCRATCH_SPACE}/arvo" 
  python3 run.py "${MAIN_COMMAND#arvo-}" checkout
  python3 run.py "${MAIN_COMMAND#arvo-}" build
  popd
fi


# OSS-FUZZ 
if [[ "$MAIN_COMMAND" == oss-* ]]; then
  # copy and build arvo cp
  if [ ! -d "$AIXCC_CP_ROOT" ]; then
    # Create the directory
    mkdir -p "$AIXCC_CP_ROOT"
    echo "Directory $AIXCC_CP_ROOT created."
  fi

  if [ ! -d "$AIXCC_CRS_SCRATCH_SPACE" ]; then
    # Create the directory
    mkdir -p "$AIXCC_CRS_SCRATCH_SPACE"
    echo "Directory AIXCC_CRS_SCRATCH_SPACE created."
  fi

  if [ ! -d "${AIXCC_CP_ROOT}/challenge-004-nginx-${MAIN_COMMAND}" ]; then
    git clone "git@github.com:Team-Atlanta/challenge-004-nginx-${MAIN_COMMAND}.git" "${AIXCC_CP_ROOT}/challenge-004-nginx-${MAIN_COMMAND}"
  fi

  pushd "${AIXCC_CP_ROOT}/challenge-004-nginx-${MAIN_COMMAND}"
    make cpsrc-prepare
  popd
fi

# synthesized cp
if [[ "$MAIN_COMMAND" == cp-* ]]; then
  # copy and build arvo cp
  if [ ! -d "$AIXCC_CP_ROOT" ]; then
    # Create the directory
    mkdir -p "$AIXCC_CP_ROOT"
    echo "Directory $AIXCC_CP_ROOT created."
  fi

  if [ ! -d "$AIXCC_CRS_SCRATCH_SPACE" ]; then
    # Create the directory
    mkdir -p "$AIXCC_CRS_SCRATCH_SPACE"
    echo "Directory AIXCC_CRS_SCRATCH_SPACE created."
  fi

  if [ ! -d "${AIXCC_CP_ROOT}/${MAIN_COMMAND}" ]; then
    git clone "git@github.com:Team-Atlanta/${MAIN_COMMAND}.git" "${AIXCC_CP_ROOT}/${MAIN_COMMAND}"
  fi

  pushd "${AIXCC_CP_ROOT}/${MAIN_COMMAND}"
    make cpsrc-prepare
  popd
fi

if [ ! $LITELLM_KEY ]; then
  echo "Need to add LITELLM_KEY in environment vars"
  exit 1
fi

if [ ! -d "$AIXCC_CP_ROOT" ] || [ -z "$(ls -A "$AIXCC_CP_ROOT")" ]; then
  build_cps
fi

export DOCKER_BUILDKIT=1

if [ ! -d "$AIXCC_CRS_SCRATCH_SPACE" ]; then
    # Create the directory
    mkdir -p "$AIXCC_CRS_SCRATCH_SPACE"
    echo "Directory AIXCC_CRS_SCRATCH_SPACE created."
fi

docker compose --profile $PROFILE build || exit -1
docker compose --profile $PROFILE up --force-recreate
