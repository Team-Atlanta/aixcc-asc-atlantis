#!/bin/bash

if [ ! $LITELLM_KEY ]; then
  echo "Need to add LITELLM_KEY in environment vars"
  exit 1
fi

PROFILE=development

CP_ROOT="./cp_root"
CP_LINUX="$CP_ROOT/challenge-001-linux-cp"
GIT_CP_LINUX="git@github.com:Team-Atlanta/challenge-001-linux-cp.git"

if [ ! -d "$CP_ROOT" ]; then
  mkdir $CP_ROOT
fi

if [ ! -d "$CP_LINUX" ]; then
  git clone $GIT_CP_LINUX $CP_LINUX
fi

(cd $CP_LINUX && git checkout -f . && git pull)
(cd $CP_LINUX && make cpsrc-prepare || exit -1)
(cd $CP_LINUX && make docker-build || exit -1)
(cd $CP_LINUX && make docker-config-local || exit -1)

docker compose --profile $PROFILE build || exit -1
docker compose --profile $PROFILE up --force-recreate
