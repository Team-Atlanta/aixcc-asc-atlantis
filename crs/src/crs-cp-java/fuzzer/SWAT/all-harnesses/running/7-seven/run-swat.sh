#!/bin/bash
rm -rf ./logs/*
PATH=/usr/lib/jvm/java-17-openjdk-amd64/bin:$PATH python3 /files/SWAT/symbolic-explorer/SymbolicExplorer.py \
 --mode active \
 --agent /files/SWAT/symbolic-executor/lib/symbolic-executor.jar \
 --z3dir /files/SWAT/libs/java-library-path \
 --logdir logs \
 --target JenkinsSeven_Concolic \
 --classpath ".:../jars/*" \
 --symbolicvars Ljava/lang/String \
 --config swat.cfg \
 --initvalue init.value \
 --port 9892 \
 -o
        
