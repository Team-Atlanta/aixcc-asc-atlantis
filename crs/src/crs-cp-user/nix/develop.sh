#!/bin/sh
nix  \
    --extra-experimental-features nix-command \
    --extra-experimental-features flakes \
    --option allow-symlinked-store true \
    develop

