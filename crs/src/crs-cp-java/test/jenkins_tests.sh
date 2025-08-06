#!/usr/bin/env bash
pushd $AIXCC_CRS_SCRATCH_SPACE/java/jenkins
./run.sh run_tests
./run.sh run_pov exemplar_only/cpv_exemplar/blobs/id_1.bin harness_id_1
