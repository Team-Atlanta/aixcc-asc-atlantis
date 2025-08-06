#!/bin/sh
cd "$(dirname "$0")"
python3 -m KasanRunner --kernel /cp-linux-build-procfs/latest_kernel \
--harness /cp-linux-build-procfs/cp-linux/out/CVE-2022-32250 \
--blob /cp_root/challenge-001-linux-cp/exemplar_only/blobs/CVE-2022-32250_solve.bin \
--work-dir /crs-workdir-procfs/kasan_test