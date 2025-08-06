#!/usr/bin/env bash

HOST_BUILD_PATH_PARENT=/home/andrew
HOST_BUILD_PATH="${HOST_BUILD_PATH_PARENT}/crs-clean"
sudo mkdir -p "$HOST_BUILD_PATH_PARENT"
sudo chown $(id -u):$(id -g) $HOST_BUILD_PATH_PARENT
sudo ln -s /out $HOST_BUILD_PATH
"$@"
