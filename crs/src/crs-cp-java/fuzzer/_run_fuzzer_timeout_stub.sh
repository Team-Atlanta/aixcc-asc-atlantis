#!/bin/bash

# Exit on any error
set -o xtrace

JAZZER_PATH="${JAZZER_PATH:=/classpath/jazzer}"

while true
do

    ${JAZZER_PATH}/jazzer "$@" || echo @@@@@ exit code of Jazzer is $? @@@@@ >&2

done
