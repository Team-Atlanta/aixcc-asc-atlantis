#!/bin/sh
export USER=$(whoami)
export NIX_IGNORE_SYMLINK_STORE=1 
. $HOME/.nix-profile/etc/profile.d/nix.sh
cd /work/nix
nix --offline \
    --extra-experimental-features nix-command \
    --extra-experimental-features flakes \
    --option allow-symlinked-store true \
    develop
