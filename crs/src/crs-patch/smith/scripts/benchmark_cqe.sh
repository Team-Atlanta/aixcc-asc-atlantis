#!/usr/bin/env bash

challenge_dirs=""

for dir in "/smith/benchmark/c/cqe/"*; do
  challenge_dirs+=" $dir"
done

# run main.py with $challenge_dirs and additional args
python3 main.py -t $challenge_dirs $@
