#!/bin/bash
rm -rf ./logs/*
PATH=/usr/lib/jvm/java-17-openjdk-amd64/bin:$PATH python3 /files/SWAT/symbolic-explorer/SymbolicExplorer.py \
 --mode active \
 --agent /app/work/java/SWAT/symbolic-executor/lib/symbolic-executor.jar \
 --z3dir /app/work/java/SWAT/libs/java-library-path \
 --logdir logs \
 --target JenkinsSix_Concolic \
 --classpath ".:../jars/*:./classes" \
 --symbolicvars Ljava/lang/String \
 --config swat.cfg \
 --initvalue init.value \
 --port 9892 \
 -o
        
