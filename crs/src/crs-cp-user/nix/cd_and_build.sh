#!/bin/sh
set -eu
cd $1
cargo b --release
