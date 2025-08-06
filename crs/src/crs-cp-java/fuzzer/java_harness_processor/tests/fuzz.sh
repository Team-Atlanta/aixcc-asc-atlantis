#!/bin/bash

if [ $# -lt 2 ]; then
    echo "Usage: $0 <CP_DIR> <CP_HARNESS_ID> [fuzzer opts]"
    exit 1
fi

CP_DIR="$(realpath "${1}")"


ID=$2

if ! [[ $ID =~ ^[0-9]+$ ]]; then
    echo "Error: HARNESS_ID should be a number"
    exit 1
fi

CP_HARNESS_ID=id_${ID}

shift
shift



SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
HARNESS_DIR="${CP_DIR}/container_scripts"


generate_harness() {
    python3 "${SCRIPT_DIR}/../main.py" -v "${CP_DIR}" "${CP_HARNESS_ID}" -p llm -o "${HARNESS_DIR}" || return -1
}

run_fuzz() {
    ID=${CP_HARNESS_ID:3}
    pushd "${CP_DIR}" > /dev/null
    
    bash run.sh fuzz "${ID}" $@
    # echo run.sh fuzz "${ID}" $@
    
    popd > /dev/null
}

generate_harness || exit 1

# renaming the harness file and file content
find "${HARNESS_DIR}" -type f -name "*PovRunner_Fuzz.*" -exec bash -c 'sed -i "s/PovRunner_Fuzz/Fuzzer_Fuzz/g" "$1"' -- {} \;
find "${HARNESS_DIR}" -type f -name "*PovRunner_Fuzz.*" -exec bash -c 'mv "$1" "${1/PovRunner_Fuzz/Fuzzer_Fuzz}"' -- {} \;

run_fuzz $@ || exit 1
