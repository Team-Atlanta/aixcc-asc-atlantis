#!/bin/bash

usage() {
    echo "Reverse a single test harness C file"
    echo "USAGE: $0 TEST_HARNESS"
}

CURR=$(readlink -f "$0")
ROOT=$(dirname "$CURR")
PLUGIN="${ROOT}/libReverserPass.so"
# PASS="mem2reg,gvn,reverser"
PASS="reverser"

SRC="$1"
BASENAME="$(basename ${1} .c)"
BC="${ROOT}/${BASENAME}.bc"
BC_TRANS="${ROOT}/${BASENAME}_trans.bc"
LL="${ROOT}/${BASENAME}.ll"
LL_TRANS="${ROOT}/${BASENAME}_trans.ll"

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

echo ">> compile the program to llvm ir"
echo "clang -c -emit-llvm -g -Xclang -disable-O0-optnone -o \"${BC}\" \"${SRC}\""
clang -c -emit-llvm -g -Xclang -disable-O0-optnone -o "${BC}" "${SRC}"
llvm-dis -o "${LL}" "${BC}"
echo ""

echo "opt -load-pass-plugin \"${PLUGIN}\" -passes=${PASS} \"${BC}\" -o \"${BC_TRANS}\""
opt -load-pass-plugin "${PLUGIN}" -passes=${PASS} "${BC}" -o "${BC_TRANS}"
llvm-dis -o "${LL_TRANS}" "${BC_TRANS}"
echo ""
