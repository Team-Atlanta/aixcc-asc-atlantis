#!/bin/bash

if [ $# -lt 4 ]; then
  exit 1
fi

CURR=$(readlink -f "$0")
ROOT=$(dirname "$CURR")
WORKDIR="$(realpath $1)"

SRC="$2"
BASENAME="$(basename ${SRC} .c)"
BC="${WORKDIR}/${BASENAME}.bc"
LL="${WORKDIR}/${BASENAME}.ll"

LINEFILE="$3"
RESULTFILE="$4"

# echo "clang -c -emit-llvm -g -Xclang -disable-O0-optnone -o \"${BC}\" \"${SRC}\""
clang -c -emit-llvm -g -Xclang -disable-O0-optnone -o "${BC}" "${SRC}"
llvm-dis -o "${LL}" "${BC}"

# echo "./macros $LL $LINEFILE $RESULTFILE"
./macros $LL $LINEFILE $RESULTFILE
