#!/bin/sh
RUNTIMES="/nix/store/nda0h04bakn2damsd06vkscwi5ds4qjd-xgcc-13.2.0-libgcc
/nix/store/n07l5k5kwxd7954wl7xk6v0qwxz536m3-libunistring-1.1
/nix/store/psfazaip7ywf3vzxfd6ngjn9zwmla7gl-libidn2-2.3.7
/nix/store/dbcw19dshdwnxdv5q2g6wldj6syyvq7l-glibc-2.39-52
/nix/store/ygbwizd4kj74myzla7drrckl3ah6ppl2-gcc-13.2.0-libgcc
/nix/store/p44qan69linp3ii0xrviypsw2j4qdcp2-gcc-13.2.0-lib"

mkdir -p out/nix/store/

for r in $RUNTIMES; do
    echo $r
    cp -r $r out/nix/store
done
