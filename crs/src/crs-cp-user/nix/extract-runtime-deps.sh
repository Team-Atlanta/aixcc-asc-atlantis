#!/bin/sh
set -eu
all_paths=""
for b in $@; do
    BIN=$b
    runs=$(readelf -d $BIN | grep \(RUNPATH\) | sed 's;^.*\[\(.*\)\].*$;\1;' | tr ':' ' ')
    for r in $runs; do
        store_paths=$(nix-store -q --references $r 2>/dev/null || :)
        all_paths=$(echo $all_paths; echo $store_paths)
    done
done
echo $all_paths | tr ' ' '\n' | sort | uniq
