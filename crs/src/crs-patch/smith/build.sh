#!/usr/bin/env bash

# Move to the directory containing this script
cd "$(dirname "$0")"

docker build . -t smith
