#! /bin/bash

CURL="curl --location --silent --user 00000000-0000-0000-0000-000000000000:secret"

until $CURL ${AIXCC_API_HOSTNAME}/health/ >/dev/null; do
	echo "Waiting for API to be available"
	sleep 5
	((c++)) && ((c == 12)) && exit 1
done

echo "Health check:"
set -x
$CURL ${AIXCC_API_HOSTNAME}/health/ | jq
set +x
echo ""

echo "Submitting VDS"
set -x
$CURL -X POST -H "Content-Type: application/json" ${AIXCC_API_HOSTNAME}/submission/vds/ -d '{"cp_name": "mock-cp", "pou": {"commit_sha1": "451dfb089f10ae0b5afd091a428e8c501c8b9b45", "sanitizer": "id_1"}, "pov": {"harness": "id_1", "data": "YWJjZGVmYWJjZGVmYWJjZGVmYWJjZGVmYWJjZGVmYWJjZGVmCmIKCjEK"}}' >vds.json
set +x
jq <vds.json
echo ""

VDS_UUID=$(jq <vds.json -r '.vd_uuid')
STATUS=$(jq <vds.json -r '.status')

while [ "$STATUS" == "pending" ]; do
	sleep 10
	echo "VDS status:"
	set -x
	$CURL "${AIXCC_API_HOSTNAME}/submission/vds/${VDS_UUID}" >vds.json
	set +x
	jq <vds.json
	echo ""
	STATUS=$(jq <vds.json -r '.status')
done

echo "Final VDS Status: ${STATUS}"
if [ "$STATUS" == "rejected" ]; then
	exit 1
fi

CPV_UUID=$(jq <vds.json -r '.cpv_uuid')
echo ""
echo "Submitting GP"
set -x
$CURL -X POST -H "Content-Type: application/json" ${AIXCC_API_HOSTNAME}/submission/gp/ -d "{\"cpv_uuid\": \"${CPV_UUID}\", \"data\": \"ZGlmZiAtLWdpdCBhL21vY2tfdnAuYyBiL21vY2tfdnAuYwppbmRleCA1NmNmOGZkLi5hYmI3M2NkIDEwMDY0NAotLS0gYS9tb2NrX3ZwLmMKKysrIGIvbW9ja192cC5jCkBAIC0xMSw3ICsxMSw4IEBAIGludCBtYWluKCkKICAgICAgICAgcHJpbnRmKCJpbnB1dCBpdGVtOiIpOwogICAgICAgICBidWZmID0gJml0ZW1zW2ldWzBdOwogICAgICAgICBpKys7Ci0gICAgICAgIGZnZXRzKGJ1ZmYsIDQwLCBzdGRpbik7CisgICAgICAgIGZnZXRzKGJ1ZmYsIDksIHN0ZGluKTsKKyAgICAgICAgaWYgKGk9PTMpe2J1ZmZbMF09IDA7fQogICAgICAgICBidWZmW3N0cmNzcG4oYnVmZiwgIlxuIildID0gMDsKICAgICB9d2hpbGUoc3RybGVuKGJ1ZmYpIT0wKTsKICAgICBpLS07Cg==\"}" >gp.json
set +x
jq <gp.json
echo ""

GP_UUID=$(jq <gp.json -r '.gp_uuid')
STATUS=$(jq <gp.json -r '.status')

while [ "$STATUS" == "pending" ]; do
	sleep 10
	echo "GP status:"
	set -x
	$CURL "${AIXCC_API_HOSTNAME}/submission/gp/${GP_UUID}" >gp.json
	set +x
	jq <gp.json
	echo ""
	STATUS=$(jq <gp.json -r '.status')
done

echo "Final GP Status: ${STATUS}"
echo ""
echo "Results"

sleep 1
