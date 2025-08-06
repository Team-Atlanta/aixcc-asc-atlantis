#! /bin/bash

printf "The following is a demonstration of a fake CRS interacting with the competition API (cAPI).  First, we'll make sure the cAPI is available.\n"

CURL="curl --location --silent"

until $CURL "${AIXCC_API_HOSTNAME}/health/" >/dev/null; do
	printf "Waiting for the cAPI to be available...\n"
	sleep 5
	((c++)) && ((c == 12)) && exit 1
done

printf "Let's run a cAPI health check before we get started.\n\n"
(
	set -x
	$CURL "${AIXCC_API_HOSTNAME}/health/"
) | jq

printf "\nIn this example, we're using an example challenge problem vulnerability (CPV) in the Mock CP, so we already know the answers.\n"
printf "But to demonstrate, let's copy to our scratch space like we would normally.\n\n"

for CP in "${AIXCC_CP_ROOT}"/*; do
	(
		set -x
		rsync --archive --delete "${CP}" "${AIXCC_CRS_SCRATCH_SPACE}"
	)
done

printf "\nWhile there may be multiple CPs in %s, we're going to go ahead and just do the Mock CP here.\n" "${AIXCC_CP_ROOT}"
CP_FOLDER="${AIXCC_CRS_SCRATCH_SPACE}/mock-cp"
cd "${CP_FOLDER}" || exit 1
printf "CPs have sources, which is where the vulnerabilities actually exist.  Mock CP has these:\n\n"
yq '.cp_sources' project.yaml
SOURCE_DIR=$(yq '.cp_sources | keys | .[0]' project.yaml)
SRC_FOLDER="${CP_FOLDER}/src/${SOURCE_DIR}"
printf "\nSome CPs may have multiple sources.  The Mock CP has only one source, in %s.\n" "${SOURCE_DIR}"
printf "At this point, a real CRS might send parts of the CP's sources off to LiteLLM (%s using the credential %s).\n" "${AIXCC_LITELLM_HOSTNAME}" "${LITELLM_KEY}"

# Assume the LLM & our CRS have produced these values
LLM_RESPONSE_COMMIT=11dafa9a5babc127357d710ee090eb4c0c05154f
read -r -d '' LLM_RESPONSE_BLOB <<-'EOF'
	abcdefabcdefabcdefabcdefabcdefabcdef
	b

	1
EOF
LLM_RESPONSE_HARNESS=filein_harness
LLM_RESPONSE_SANITIZER="AddressSanitizer: global-buffer-overflow"

printf "Then it would test the responses using the local copy of the CP.\n\n"

BLOB_FILE=$(mktemp)
printf "%s\n" "$LLM_RESPONSE_BLOB" >"$BLOB_FILE"
cd "${SRC_FOLDER}" || exit 1
git checkout "${LLM_RESPONSE_COMMIT}" >/dev/null 2>/dev/null
cd "${CP_FOLDER}" || exit 1
# First, build the CP
./run.sh build
# Then, test our blob with the harness & check if the sanitizer fired
(
	set -x
	./run.sh run_pov "${BLOB_FILE}" "${LLM_RESPONSE_HARNESS}"
)
find out -type f -iname 'std*.log' | grep run_pov | xargs cat
if find out -type f -iname 'std*.log' | grep run_pov | xargs cat | (
	set -x
	grep "${LLM_RESPONSE_SANITIZER}" -q
); then
	printf "\nLooks like our sanitizer fired, as expected.\n"
else
	printf "\nOur sanitizer did not fire, so we've got to start all over.\n"
	exit 1
fi

printf "Now that we've confirmed that our VDS works, let's submit it.\n"
printf "Using the contents of the CP's project.yaml, we can convert our harness & sanitizer to the CP's canonical names.\n\n"
cd "${CP_FOLDER}" || exit 1
HARNESS_ID=$(
	set -x
	yq '.harnesses | to_entries | filter(.value.name == "'"${LLM_RESPONSE_HARNESS}"'") | .[].key' project.yaml
)
SANITIZER_ID=$(
	set -x
	yq '.sanitizers | to_entries | filter(.value == "'"${LLM_RESPONSE_SANITIZER}"'") | .[].key' project.yaml
)
B64_BLOB=$(printf "%s\n" "${LLM_RESPONSE_BLOB}" | base64 -w 0)
VDS_DATA=$(printf "{\"cp_name\": \"Mock CP\", \"pou\": {\"commit_sha1\": \"%s\", \"sanitizer\": \"%s\"}, \"pov\": {\"harness\": \"%s\", \"data\": \"%s\"}}" "$LLM_RESPONSE_COMMIT" "$SANITIZER_ID" "$HARNESS_ID" "$B64_BLOB")

printf "\nNow that we have the inputs we need for the API, we can go ahead and submit our VDS.\n\n"
(
	set -x
	$CURL -X POST -H "Content-Type: application/json" "${AIXCC_API_HOSTNAME}/submission/vds/" -d "${VDS_DATA}" >vds.json
)
jq <vds.json
VDS_UUID=$(jq <vds.json -r '.vd_uuid')

printf "\nThe cAPI is now evaluating our Vulnerability Discovery Submission (VDS).  Its status will be pending until the cAPI runs all the tests.\n\n"
(
	set -x
	$CURL "${AIXCC_API_HOSTNAME}/submission/vds/${VDS_UUID}"
) >vds.json
STATUS=$(jq <vds.json -r '.status')
while [ "$STATUS" == "pending" ]; do
	sleep 10
	printf "\nWaiting for VDS to finish testing...\n\n"
	(
		set -x
		$CURL "${AIXCC_API_HOSTNAME}/submission/vds/${VDS_UUID}" >vds.json
	)
	jq <vds.json
	STATUS=$(jq <vds.json -r '.status')
done

printf "\nAt this point, the VDS has been fully tested.  It could either be accepted or rejected.\n"
if [ "$STATUS" == "rejected" ]; then
	printf "Our VDS was rejected, so we've got to start over.\n"
	exit 1
fi
printf "Our VDS was accepted, so we should move on to producing a Generated Patch (GP).\n"
printf "A real CRS would be asking an LLM to produce a patch file now.\n"

# Assume the LLM & our CRS have produced this patch
read -r -d '' LLM_RESPONSE_PATCH <<-'EOF'
	diff --git a/mock_vp.c b/mock_vp.c
	index 56cf8fd..abb73cd 100644
	--- a/mock_vp.c
	+++ b/mock_vp.c
	@@ -11,7 +11,8 @@ int main()
	         printf("input item:");
	         buff = &items[i][0];
	         i++;
	-        fgets(buff, 40, stdin);
	+        fgets(buff, 9, stdin);
	+        if (i==3){buff[0]= 0;}
	         buff[strcspn(buff, "\n")] = 0;
	     }while(strlen(buff)!=0);
	     i--;
EOF

CPV_UUID=$(jq <vds.json -r '.cpv_uuid')
printf "We need that CPV UUID from the last status response, which the cAPI assigned to us.  Looks like it's %s.\n" "$CPV_UUID"
printf "Now that we've got our CPV UUID and our patch, let's submit it.\n\n"
PATCH_B64=$(printf "%s\n" "$LLM_RESPONSE_PATCH" | base64 -w 0)
GP_DATA=$(printf "{\"cpv_uuid\": \"${CPV_UUID}\", \"data\": \"%s\"}" "$PATCH_B64")
(
	set -x
	$CURL -X POST -H "Content-Type: application/json" "${AIXCC_API_HOSTNAME}/submission/gp/" -d "${GP_DATA}" >gp.json
)
jq <gp.json
GP_UUID=$(jq <gp.json -r '.gp_uuid')

printf "\nNow we wait while the cAPI evaluates our GP.\n"
$CURL "${AIXCC_API_HOSTNAME}/submission/gp/${GP_UUID}" >gp.json
STATUS=$(jq <gp.json -r '.status')
while [ "$STATUS" == "pending" ]; do
	sleep 10
	printf "Waiting for GP to finish testing...\n\n"
	(
		set -x
		$CURL "${AIXCC_API_HOSTNAME}/submission/gp/${GP_UUID}" >gp.json
	)
	jq <gp.json
	STATUS=$(jq <gp.json -r '.status')
done

printf "\nThe cAPI has finished testing our GP.  As with the VDS, our GP could be accepted or rejected at this point.\n"
printf "Final GP Status: %s\n" "${STATUS}"
printf "For more information on what was done here, there are logs available in docker-compose, as well as an audit log that the cAPI produced.\n"
printf "Look at the outputs of \`make logs-nofollow\` (for all the services) and \`make logs-crs-nofollow\` (for the CRS's logs only).\n"
printf "There are a few other make targets available to show you logs for crs-sandbox, including \`make logs-capi-audit\`.\n"
