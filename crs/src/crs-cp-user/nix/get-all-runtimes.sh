#!/bin/sh
RUNTIMES="\-glibc-2.39-52
\-xgcc-13.2.0-libgcc
\-gcc-13.2.0-lib
\-libidn2-2.3.7
\-libunistring-1.1
\-gcc-13.2.0-libgcc"

for r in $RUNTIMES; do
    fd "$r\$" /nix/store
done
