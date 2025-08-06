#!/usr/bin/env bash

set -e

# print warning
warn() {
	echo "$*" >&2
}

# exit function that prints a message to stderr and then fails the script
die() {
	warn "$*"
	exit 1
}

# find actual wrapper functions
SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../src/scripts/iapi_functions.sh"

#################################
## Test logic
#################################

# test health/status commands
if iapi_status_good; then echo "Passed status check"; else die "Failed status check"; fi
if iAPI_HEALTH_GOOD="bad" iapi_status_good; then die "Failed incorrect status check"; else echo "Passed incorrect status check"; fi
if iAPI_HEALTH_CMD="invalid" iapi_status_good; then die "Failed invalid health command"; else echo "Passed invalid health command"; fi
if iAPI_HEALTH_FIELD="invalid" iapi_status_good; then die "Failed invalid status JSON field check"; else echo "Passed invalid status JSON field check"; fi

# test VDS functions
test_vds_data_valid='{"cp_name":"linux kernel","pou":{"commit_sha1":"2923ffa6e0572ee6572245f980acfcfb872fcf74","sanitizer":"id_1"},"pov":{"harness":"id_2","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG4iKTsNCisJcmV0dXJuIDA7DQogfQ=="}}'
test_vds_data_valid_binary='{"cp_name":"linux kernel","pou":{"commit_sha1":"2923ffa6e0572ee6572245f980acfcfb872fcf74","sanitizer":"id_1"},"pov":{"harness":"id_2","data":"i4uLi4WLi4uLi4uLi4uLi4uLi4xQi4uLi4uLjIuLiw=="}}'
test_vds_data_invalid_sha='{"cp_name":"linux kernel","pou":{"commit_sha1":"2923ffa6e0572ee6572245f980acf","sanitizer":"id_1"},"pov":{"harness":"id_2","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG4iKTsNCisJcmV0dXJuIDA7DQogfQ=="}}'
test_vds_data_invalid_sanitizer='{"cp_name":"linux kernel","pou":{"commit_sha1":"2923ffa6e0572ee6572245f980acfcfb872fcf74","sanitizer":"not an id"},"pov":{"harness":"id_2","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG4iKTsNCisJcmV0dXJuIDA7DQogfQ=="}}'
test_vds_data_invalid_harness='{"cp_name":"linux kernel","pou":{"commit_sha1":"2923ffa6e0572ee6572245f980acfcfb872fcf74","sanitizer":"ASAN: slab-out-of-bounds"},"pov":{"harness":"mux_test_harness","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG4iKTsNCisJcmV0dXJuIDA7DQogfQ=="}}'
test_vds_data_invalid_data='{"cp_name":"linux kernel","pou":{"commit_sha1":"2923ffa6e0572ee6572245f980acfcfb872fcf74","sanitizer":"id_1"},"pov":{"harness":"id_2","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3!!@#!@#KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG"}}'
test_vds_data_missing_cp='{"pou":{"commit_sha1":"2923ffa6e0572ee6572245f980acfcfb872fcf74","sanitizer":"id_1"},"pov":{"harness":"id_2","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3!!@#!@#KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG"}}'
test_vds_data_null_pou='{"cp_name":"linux kernel","pou":null,"pov":{"harness":"id_2","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG4iKTsNCisJcmV0dXJuIDA7DQogfQ=="}}'

if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_valid}" | wc -c) -eq 37 ]]; then echo "Passed VDS vd_uuid check"; else die "Failed VDS vd_uuid check"; fi
if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_valid_binary}" | wc -c) -eq 37 ]]; then echo "Passed VDS binary POV blob check"; else die "Failed VDS binary POV blob check"; fi
if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_invalid_sha}" | wc -c) -eq 37 ]]; then die "Failed VDS submission with invalid hash check"; else echo "Passed VDS submission with invalid hash check"; fi
if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_invalid_sanitizer}" | wc -c) -eq 37 ]]; then die "Failed VDS submission with invalid sanitizer check"; else echo "Passed VDS submission with invalid sanitizer check"; fi
if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_invalid_harness}" | wc -c) -eq 37 ]]; then die "Failed VDS submission with invalid harness check"; else echo "Passed VDS submission with invalid harness check"; fi
if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_invalid_data}" | wc -c) -eq 37 ]]; then die "Failed VDS submission with invalid data check"; else echo "Passed VDS submission with invalid data check"; fi
if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_missing_cp}" | wc -c) -eq 37 ]]; then die "Failed VDS submission with missing CP check"; else echo "Passed VDS submission with missing CP check"; fi
if [[ $(iapi_post_vds_vd_uuid "-d ${test_vds_data_null_pou}" | wc -c) -eq 37 ]]; then die "Failed VDS submission with null POU check"; else echo "Passed VDS submission with null POU check"; fi

test_vd_uuid_valid="16468b28-a301-4302-a2e8-17e37bf41220"
test_vd_uuid_invalid="16468b28-a301-2302-a2e8-17e37bf41220"
test_vd_uuid_invalid2="16468b28-a301-2302-a2e8"
if iapi_vds_submission_api_accepted "${test_vd_uuid_valid}"; then echo "Passed VDS status #1 check"; else die "Failed VDS status #1 check"; fi
if iapi_vds_submission_not_rejected "${test_vd_uuid_valid}"; then echo "Passed VDS status #2 check"; else die "Failed VDS status #2 check"; fi
if iapi_vds_submission_finished "${test_vd_uuid_valid}"; then echo "Passed VDS status #3 check"; else die "Failed VDS status #3 check"; fi
if iapi_vds_submission_passed "${test_vd_uuid_valid}"; then echo "Passed VDS status #4 check"; else die "Failed VDS status #4 check"; fi
if iapi_vds_submission_api_accepted "${test_vd_uuid_invalid}"; then die "Failed invalid VDS UUID #1 check"; else echo "Passed invalid VDS UUID #1 check"; fi
if iapi_vds_submission_api_accepted "${test_vd_uuid_invalid2}"; then die "Failed invalid VDS UUID #2 check"; else echo "Passed invalid VDS UUID #2 check"; fi
if iapi_vds_submission_api_accepted ""; then die "Failed invalid VDS UUID #3 check"; else echo "Passed invalid VDS UUID #3 check"; fi
if iAPI_GET_VDS_CMD="get invalid" iapi_vds_submission_api_accepted "${test_vd_uuid_valid}"; then die "Failed invalid get VDS command check"; else echo "Passed invalid get VDS command check"; fi
if iAPI_VDS_STATUS_FIELD="invalid" iapi_vds_submission_api_accepted "${test_vd_uuid_valid}"; then die "Failed invalid VDS status field check"; else echo "Passed invalid VDS status field check"; fi
if [[ $(iapi_get_vds_cpv_uuid "${test_vd_uuid_valid}" | wc -c) -eq 37 ]]; then echo "Passed VDS cpv_uuid check"; else die "Failed VDS cpv_uuid check"; fi

# # test GP functions
test_gp_data_valid='{"cpv_uuid":"17820e40-2a2b-4de1-931f-72cefb6d490d","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG4iKTsNCisJcmV0dXJuIDA7DQogfQ=="}'
test_gp_data_invalid_cpv_uuid='{"cpv_uuid":"17820e40-2a2b-2de1-931f-72cefb6d490d","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGYoIkhlbGxvIFdvcmxkXG4iKTsNCisJcmV0dXJuIDA7DQogfQ=="}'
test_gp_data_invalid_data='{"cpv_uuid":"17820e40-2a2b-2de1-931f-72cefb6d490d","data":"LS0tIGhlbGxvLmMJMjAxNC0xMC0wNyAxODoxNzo0OS4wMDAwMDAwMDAgKzA1MzANCisrKyBoZWxsb19uZXcuYwkyMDE0LTEwLTA3IDE4OjE3OjU0LjAwMDAwMDAwMCArMDUzMA0KQEAgLTEsNSArMSw2IEBADQogI2luY2x1ZGUgPHN0ZGlvLmg+DQogDQotaW50IG1haW4oKSB7DQoraW50IG1haW4oaW50IGFyZ2MsIGNoYXIgKmFyZ3ZbXSkgew0KIAlwcmludGY!@#$!#sdaf"}'
if [[ $(iapi_post_gp_gp_uuid "-d ${test_gp_data_valid}" | wc -c) -eq 37 ]]; then echo "Passed GP gp_uuid check"; else die "Failed GP gp_uuid check"; fi
if [[ $(iapi_post_gp_gp_uuid "-d ${test_gp_data_invalid_cpv_uuid}" | wc -c) -eq 37 ]]; then die "Failed GP submission with invalid GP UUID check"; else echo "Passed GP submission with invalid GP UUID check"; fi
if [[ $(iapi_post_gp_gp_uuid "-d ${test_gp_data_invalid_data}" | wc -c) -eq 37 ]]; then die "Failed GP submission with invalid patch check"; else echo "Passed GP submission with invalid patch check"; fi

test_gp_uuid_valid="23468b28-a341-4402-a248-17e37bf41212"
test_gp_uuid_invalid="23468b28-a341-2402-a248-17e37bf41212"
test_gp_uuid_invalid2="23468b28-a341-e37bf41212"
if iapi_gp_submission_api_accepted "${test_gp_uuid_valid}"; then echo "Passed GP status #1 check"; else die "Failed GP status #1 check"; fi
if iapi_gp_submission_not_rejected "${test_gp_uuid_valid}"; then echo "Passed GP status #2 check"; else die "Failed GP status #2 check"; fi
if iapi_gp_submission_finished "${test_gp_uuid_valid}"; then echo "Passed GP status #3 check"; else die "Failed GP status #3 check"; fi
if iapi_gp_submission_built "${test_gp_uuid_valid}"; then echo "Passed GP status #4 check"; else die "Failed GP status #4 check"; fi
if iapi_gp_submission_api_accepted "${test_gp_uuid_invalid}"; then die "Failed invalid GP UUID #1 check"; else echo "Passed invalid GP UUID #1 check"; fi
if iapi_gp_submission_api_accepted "${test_gp_uuid_invalid2}"; then die "Failed invalid GP UUID #2 check"; else echo "Passed invalid GP UUID #2 check"; fi
if iapi_gp_submission_api_accepted ""; then die "Failed invalid GP UUID #3 check"; else echo "Passed invalid GP UUID #3 check"; fi
if iAPI_GET_GP_CMD="get invalid" iapi_gp_submission_api_accepted "${test_gp_uuid_valid}"; then die "Failed invalid get GP command check"; else echo "Passed invalid get GP command check"; fi
if iAPI_GP_STATUS_FIELD="invalid" iapi_gp_submission_api_accepted "${test_gp_uuid_valid}"; then die "Failed invalid GP status field check"; else echo "Passed invalid GP status field check"; fi
