#!/bin/bash

set -e

# for my setup of JAVA_HOME:
#export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# build java part
#mvn install:install-file -Dfile=./jars/py4j-0.10.9.7.jar -DgroupId=py4j -DartifactId=py4j -Dversion=0.10.9.7 -Dpackaging=jar
mvn clean compile assembly:single

# install python requirement
virtualenv -p python3 venv
. venv/bin/activate
pip install -r requirements.txt
deactivate
