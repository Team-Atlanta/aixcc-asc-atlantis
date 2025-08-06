#!/usr/bin/env bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <path-to-benchmark>"
  exit 1
fi

docker run -v $1:/benchmark -v $(pwd):/smith -it --rm -w /smith smith /bin/bash