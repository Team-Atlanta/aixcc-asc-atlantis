#!/bin/bash
./concolic-fuzzing.py \
	-s "/files/SWAT" \
	-c "PipelineCommandUtilFuzzer" \
	-l "logs"\
	-p ".:classes/jars/*:../jars/*" \
	-v "Ljava/lang/String" \
	-f "./corpus" \
	-C "./concolic-corpus" \
	--no-swat-output \
	--prioritize-concolic \
	--port 9892
