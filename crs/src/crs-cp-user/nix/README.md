Build environment that's independent of base Linux distribution.

TODO
- install on host + offline install in guest + copy nix store to guest
- symlink or bind mount nix store to /out
- bootstrap script for every `run.sh custom` invocation
- build python lib statically and port testlang\_fuzz build
- test on nginx and arvo

# Downloading Nix
```
cd ../assets
wget https://releases.nixos.org/nix/nix-2.23.0/nix-2.23.0-x86_64-linux.tar.xz
tar xf nix-2.23.0-x86_64-linux.tar.xz
```

# Download, install, and archive Nix and shell dependencies on host
```
cd ../nix
./bootstrap-nix-host.sh
```

Note to self: this should be done at CRS Docker build time.

# Build fuzzer in host
Could try to use a host-compiled fuzzer in CP container. Currently has issue if
libafl\_cc tries to link a clang library, e.g. `libno-link-rt.a` for arvo-10762.

```
cd ../libafl_libfuzzer
cargo vendor
# copy the output of prev command to ./.cargo/config.toml
cargo b --release
# If we need -fPIC
# RUSTFLAGS='-C relocation-model=pic' \
#    cargo b --release
```

Do the same for libafl\_hybrid.

Note to self: this should be done at CRS Docker build time.

# Copying things into CP
```
cd ..                               # go to CRS root
cp -r libafl_libfuzzer $CP/out
cp -r libafl_hybrid $CP/out
cp -r third_party $CP/out           # build.rs modified here! update if already copied
cp -r testlang_fuzz $CP/out         # if using testlang-mutator
cp -r nix/* $CP/out
cp -r assets/nix-2.23.0-x86_64-linux $CP/out

mkdir -p $CP/work/nix
mv $CP/out/flake.nix $CP/work/nix/
mv $CP/out/flake.lock $CP/work/nix/

# mounts seem to be illegal in docker?
# # bind nix store to CP
# mkdir -p $CP/out/nix
# sudo mount --bind /nix $CP/out/nix

# optional
git clone --recurse-submodules https://github.com/eurecom-s3/symcc.git $CP/out/symcc 
```

# Copy runtime nix deps into CP container
We will copy subset of nix store into `crs_scratch` and then volume
mount it, or copy to `$CP/out` and 
`sudo cp -r /out/nix /nix; sudo chown -R $(id -u):$(id -g)`.
Former seems more efficient, as long as volume mounting works fine in CRS env.

On host in $CP:
```
out/runtimes.sh
```

Runtimes were collected via `readelf -d target/release/libafl_cc`. Either we
parse this output for each library/binary we need, or we recursively find the
appropriate directories in `/nix/store`. Or we hardcode, if `flakes.lock`
actually makes the nix store paths idempotent.

More info https://nixos.org/guides/nix-pills/09-automatic-runtime-dependencies

# TODO CP build wrapper for libafl_cc local dependencies

# (build wrapper WIP) Build CP
If this fails, then try to build the fuzzer in the container.

```
cd $CP
mv out/build-cp.sh .
./build-cp.sh
```

# Enter CP container
```
cd $CP
out/interactive.sh
```

The following steps in this README are meant to be done in an interactive shell
in the CP container. 

```
unset CC CXX CFLAGS CXXFLAGS
```

# Installing Nix
```
/out/install-nix.sh
```

# Spawning dev shell
```
/out/spawn-nix-shell.sh
```

Perform the subsequent steps inside this shell. Later we'll use the `-c` option
to run a script inside the nix environment.

# (outdated) Building libafl\_libfuzzer
```
cd /out/libafl_libfuzzer
cargo b --release
```

# (optional) Building standalone symcc
```
cd /out/symcc
mkdir -p build
cd build
cmake -G Ninja -DSYMCC_RT_BACKEND=qsym -DZ3_DIR=$(dirname $(fd libz3\.so /nix/store | head -n1)) -DZ3_TRUST_SYSTEM_VERSION=ON ..
ninja check
```

# (outdated) Building libafl\_hybrid
```
cd /out/libafl_hybrid/runtime
LLVM_DIR=$(dirname $(fd LLVMConfig\.cmake /nix/store | head -n1)) cargo b --release

cd /out/libafl_hybrid/fuzzer
LLVM_DIR=$(dirname $(fd LLVMConfig\.cmake /nix/store | head -n1)) cargo b --release
```

# Building nginx harness with libafl\_libfuzzer
General steps, modify if something's wrong.
NOTE `libafl_libfuzzer/src/bin/libafl_cc.rs` modified, copy over to CP.

In host CP directory
```
cp container_scripts/cp_build.tmpl out
./run.sh custom env > out/custom-env
```

In CP docker
```
sudo su       # optional, sometimes the CP requires root privs
. /out/custom-env
cd /src/nginx # optional? OSS-Fuzz builds starting in the source dir
bash /out/cp_build.tmpl
```

The following variables are old attempts, kept for future reference. DO NOT USE.
In Docker CP, *outside* of nix environment
```
export LD_LIBRARY_PATH=/usr/lib 
export CC=/out/libafl_libfuzzer/target/release/libafl_cc 
export CXX=/out/libafl_libfuzzer/target/release/libafl_cxx 
# export LD=/usr/bin/ld
# export CC=/usr/local/bin/clang
# export CXX=/usr/local/bin/clang++
export LDFLAGS="$LDFLAGS -L/usr/lib"  
export NIX_LDFLAGS="$NIX_LDFLAGS -L/usr/lib"  
# export LD_DEBUG=all
export NIX_DEBUG=1
export CFLAGS="$CFLAGS -isystem /usr/include"
export NIX_CFLAGS_COMPILE="$NIX_CFLAGS_COMPILE -isystem /usr/include"
export NIX_ENFORCE_PURITY=0
export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig
bash cp_build.tmpl
```
