#!/bin/sh

set -eu

export USER=$(whoami)
export NIX_IGNORE_SYMLINK_STORE=1 

NIX_VERSION="nix-2.23.0"
NIX_INSTALLER="${NIX_VERSION}-x86_64-linux"

cd /out/$NIX_INSTALLER
./install --yes --no-daemon --no-channel-add


# . $HOME/.nix-profile/etc/profile.d/nix.sh

# or symlink if it works
# DEVSHELL=/tmp/devshell

# 28 seconds to cp -r /out/nix /nix

# copy at every invocation

# if [ -d "$DEVSHELL" ]; then
#     sudo rm -rf "$DEVSHELL"
# fi
# sudo mkdir -p "$DEVSHELL"
# sudo chown $(id -u):$(id -g) "$DEVSHELL"
# cd $DEVSHELL
# cp /out/flake.nix $DEVSHELL/
# cp -r /out/devshell $DEVSHELL/
# nix \
#     --option allow-symlinked-store true \
#     --offline \
#     --extra-experimental-features nix-command \
#     --extra-experimental-features flakes \
#     copy \
#     --from "file:///out/devshell?compression=none" \
#     --all
#     # '.#devShells.x86_64-linux.default'


# sudo cp -ar /out/nix /nix
