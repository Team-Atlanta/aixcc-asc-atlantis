#!/bin/sh

SCRIPT_ROOT=$(dirname $(realpath $0))
CRS_ROOT=$(realpath "${SCRIPT_ROOT}/..")
NIX_VERSION="nix-2.23.0"
NIX_INSTALLER="${NIX_VERSION}-x86_64-linux"
NIX_TAR="${NIX_INSTALLER}.tar.xz"
NIX_URL="https://releases.nixos.org/nix/${NIX_VERSION}/${NIX_TAR}"

export NIX_IGNORE_SYMLINK_STORE=1 

# download and unpack
cd $CRS_ROOT/assets

if ! [ -d "$NIX_INSTALLER" ]; then
    wget $NIX_URL
    tar xf "$NIX_TAR"
fi

# install
cd $NIX_INSTALLER
./install --yes --no-daemon --no-channel-add # needs sudo access

# download dependencies
cd $SCRIPT_ROOT
. $HOME/.nix-profile/etc/profile.d/nix.sh
nix \
    --extra-experimental-features nix-command \
    --extra-experimental-features flakes \
    --option allow-symlinked-store true \
    develop \
    --command bash -c ':'

# NOTE Symlink'd nix store is broken!!! really mad
#      This pretty much breaks all reasonable attempts at saving store outside of CP container
#      without copying it to /nix every time we ./run.sh
# if ! [ -d "/tmp" ]; then
#     sudo mkdir /tmp
# fi

# ln -sf $SCRIPT_ROOT /tmp/devshell
# cd /tmp/devshell

# NOTE Binary cache nix copy is broken!!! really mad
#      Other methods are cp -r /nix, nix store --export
# export to binary cache
# 46 seconds without compression
# nix \
#     --extra-experimental-features nix-command \
#     --extra-experimental-features flakes \
#     --option allow-symlinked-store true \
#     copy \
#     --to "file://${SCRIPT_ROOT}/devshell?compression=none" '.#devShells.x86_64-linux.default'
