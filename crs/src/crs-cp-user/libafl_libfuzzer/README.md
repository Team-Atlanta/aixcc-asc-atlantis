# libafl\_cc Based In-Process Fuzzing Toolchain

**Current Status:** Instrumentation and fuzzing work for nginx and mock cp. NGINX pov can be reproduced.

## Introduction

Since the nginx harness resets the global state each time, we aim to compile the harness and fuzzer together to enable in-process fuzzing. 

The idea is to incorporate all fuzzing logic into a static library. By using a compiler wrapper (`libafl_cc`), we can instrument the target challenges with custom compiler flags and link the harness with the static library. 

However, we cannot access the Dockerfile and network during ASC. Therefore, we need to copy all the Rust toolchains to the shared folder. 

Please check `bin/libafl_cc.rs` for more details.

## Using Local Cargo Registry

```bash
# Install cargo-local-registry
cargo install cargo-local-registry

cargo local-registry --sync ./Cargo.lock local-registry

# Build test
cargo build --offline --release
```

## Copy rust toolchains and regisries

```bash

# fuzzer
cp -r ./libafl_libfuzzer $CP/out
cp -r ./third_party $CP/out


# rust toolchains
mkdir -p $CP/out/rust
cp -r ~/.rustup $CP/out/rust
cp -r ~/.cargo $CP/out/rust

# util scripts
cp ./build-libaflcc.sh $CP/out

# challenge project build wrapper
cp ./build-cp.sh $CP

# fuzzer script
cp ./fuzz.sh $CP/out

# (optional) copy NGINX token dictionary
# @Joseph integrate this step or another approach
cp ./http_request_fuzzer.dict $CP/out

# (optional) test harness.c
cp ./harness.c $CP/out
```

## Build libafl\_cc in Docker

```bash

cd $CP

# disable docker network and build libafl compiler
DOCKER_EXTRA_ARGS="--network none"  ./run.sh custom /out/build-libaflcc.sh


# (optional) the rest of these commands are unnecessary if using build-cp.sh (see section below)
cd $CP/out/libafl_libfuzzer/target/release
cp libskynet_libfuzzer.a libskynet_libfuzzer.bak.a

# (optional)
objcopy libskynet_libfuzzer.a \
    --redefine-sym writev=__real_writev \
    --redefine-sym open=__real_open \
    --redefine-sym getsockopt=__real_getsockopt \
    --redefine-sym select=__real_select \
    --redefine-sym recv=__real_recv \
    --redefine-sym read=__real_read \
    --redefine-sym send=__real_send \
    --redefine-sym epoll_create=__real_epoll_create \
    --redefine-sym epoll_create1=__real_epoll_create1 \
    --redefine-sym epoll_wait=__real_epoll_wait \
    --redefine-sym epoll_ctl=__real_epoll_ctl \
    --redefine-sym close=__real_close \
    --redefine-sym ioctl=__real_ioctl \
    --redefine-sym listen=__real_listen \
    --redefine-sym accept=__real_accept \
    --redefine-sym accept4=__real_accept4 \
    --redefine-sym setsockopt=__real_setsockopt \
    --redefine-sym bind=__real_bind \
    --redefine-sym shutdown=__real_shutdown \
    --redefine-sym connect=__real_connect \
    --redefine-sym getpwnam=__real_getpwnam \
    --redefine-sym getgrnam=__real_getgrnam \
    --redefine-sym chmod=__real_chmod \
    --redefine-sym chown=__real_chown \
    libskynet_modified.a

# (optional)
cp libskynet_modified.a libskynet_libfuzzer.a
```

## Instrumentation using libafl\_cc

```bash

# (optional) testing a simple harness
./run.sh custom /out/libafl_libfuzzer/target/release/libafl_cc /out/libafl_libfuzzer/harness.c -o /out/target


# build the harness with instrumentation
./build-cp.sh

```

## Run the fuzzer

```
# Create initial corpus if doesn't exist
mkdir -p /out/corpus; echo "AAA" > /out/corpus/dummy
./run.sh custom /out/fuzz.sh
```

