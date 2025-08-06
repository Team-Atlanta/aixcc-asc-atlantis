#!/bin/sh

harnesses=$(yq -r '.harnesses[] | .binary' project.yaml | xargs -I _ basename _ | tr '\n' ':' | sed '$s/:$//')

DOCKER_BUILD_PREFIX="-e CP_HARNESS_BUILD_PREFIX=/out/build-wrapper.sh -e CP_BASE_BUILD_PREFIX=/out/build-wrapper.sh"

DOCKER_EXTRA_ARGS="${DOCKER_EXTRA_ARGS} -e CC=/out/skytool/libafl_cc -e CXX=/out/skytool/libafl_cxx -e CP_HARNESS=${harnesses} ${DOCKER_BUILD_PREFIX}" ./run.sh -v build

# Binary *should* be in a mounted dir since build needs it to be persistent. Can copy it at the host level
for h in $(yq -r .harnesses[].binary project.yaml); do
    if [ -f "$h" ] && ! [ "$h" =  out/$(basename "$h") ]; then
        cp "$h" out/$(basename "$h")
    fi
done
