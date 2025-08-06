#!/bin/sh
. ./.env.project
docker run \
       --network none \
       -v $(pwd)/work:/work \
       -v $(pwd)/src:/src \
       -v $(pwd)/out:/out \
       -v /nix:/nix \
       --env-file $(pwd)/.env.docker \
       -it \
       -e LOCAL_USER=$(id -u):$(id -g) \
       $DOCKER_IMAGE_NAME \
       /bin/bash
