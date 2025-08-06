set -x

FUZZER_DIR=../../../
SKYTRACER_DIR=$FUZZER_DIR/SkyTracer
SYZKALLER_DIR=$FUZZER_DIR/syzkaller
WORK_DIR=./workdir/

# Build
set -e
$SYZKALLER_DIR/tools/syz-env make reverser

# Run
set +e
for testlang in ../../../reverser/answers/linux_test_harness.txt; do
	HARNESS_ID=$(basename $testlang .txt)
	$SYZKALLER_DIR/bin/syz-reverser \
		-syzkaller $SYZKALLER_DIR \
		-tracer $SKYTRACER_DIR/skytracer.py \
		-kernel $SKYTRACER_DIR/skytracer-linux/ \
		-work $WORK_DIR \
		-harness_id $HARNESS_ID \
		-harness $SKYTRACER_DIR/skytracer-linux/test_harnesses/$HARNESS_ID.c \
		-testlang $testlang \
		-output $WORK_DIR/$HARNESS_ID.txt
done
