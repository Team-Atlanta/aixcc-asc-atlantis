#!/bin/bash

export RUSTUP_HOME=/out/rust/.rustup
export CARGO_HOME=/out/rust/.cargo
export PATH=$CARGO_HOME/bin:$PATH
export LLVM_CONFIG=llvm-config

cd /out/libafl_libfuzzer

cargo build --release --offline
