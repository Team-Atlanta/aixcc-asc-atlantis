#!/bin/bash

[ $# -lt 3 ] && echo "Usage: $0 <this-repo-jar> <cp-source-dir> <harness-dirs>" && exit 1

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

. ${SCRIPT_DIR}/venv/bin/activate

JARPATH=$1
CP_SOURCE_DIR=$2
shift
shift

python3 ${SCRIPT_DIR}/server.py -j ${JARPATH} -cp ${CP_SOURCE_DIR} -d "$@"

deactivate