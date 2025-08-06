#!/bin/bash

if [ ! $LITELLM_KEY ]; then
  echo "Need to add LITELLM_KEY in environment vars"
  exit 1
fi

if [ ! $LITELLM_HOSTNAME ]; then
  echo "Need to add LITELLM_HOSTNAME in environment vars"
  exit 1
fi

PROFILE=development

CP_ROOT="./cp_root"
if [ ! -d "$CP_ROOT" ]; then
  mkdir $CP_ROOT
fi

CP_LINUX="$CP_ROOT/cp-linux"
GIT_CP_LINUX="git@github.com:Team-Atlanta/challenge-001-linux-cp.git"
if [ ! -d "$CP_LINUX" ]; then
  git clone $GIT_CP_LINUX $CP_LINUX
fi
(cd $CP_LINUX && git checkout -f . && git pull)

CP_JENKINS="$CP_ROOT/cp-jenkins"
GIT_CP_JENKINS="git@github.com:Team-Atlanta/asc-challenge-002-jenkins-cp.git"
if [ ! -d "$CP_JENKINS" ]; then
  git clone $GIT_CP_JENKINS $CP_JENKINS
fi
(cd $CP_JENKINS && git checkout -f . && git pull)

# CP_USERSPACE="$CP_ROOT/cp-libjpeg-turbo"
# GIT_CP_USERSPACE="git@github.com:Team-Atlanta/cp-libjpeg-turbo-exemplar.git"
# if [ ! -d "$CP_USERSPACE" ]; then
#   git clone $GIT_CP_USERSPACE $CP_USERSPACE
# fi
# (cd $CP_USERSPACE && git checkout -f . && git pull)

CRS_SCRATCH="/crs_scratch"
if [ ! -d "$CRS_SCRATCH" ]; then
  sudo mkdir $CRS_SCRATCH
fi

CRS_REQUESTS="$CRS_SCRATCH/requests"
if [ ! -d "$CRS_REQUESTS" ]; then
  sudo mkdir $CRS_REQUESTS
fi

docker compose --profile $PROFILE build || exit -1
docker compose --profile $PROFILE up