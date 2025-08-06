#!/bin/bash
test_parser() {
    echo "Testing parser"
    python3 -m unittest tests.test_parser
}


test_generator() {
    echo "Testing generator"
    python3 -m unittest tests.test_generator
}

test_realsetting() {
    echo "Testing real setting"
    python3 -m unittest tests.test_realsetting
}

run_test() {
    test_parser
    test_generator
    test_realsetting
}

if [ -z "$1" ]; then
    echo "Usage: run_test.sh <path_to_cp_dir>"
    exit 1
fi

# change directory to this file path


export CP_DIR=$(realpath $1)

if [ "$2" = "--no-compile" ]; then
    export COMPILE_TEST="disabled"
else
    export COMPILE_TEST="enabled"
fi

pushd "$(dirname "$0")"
run_test
popd
