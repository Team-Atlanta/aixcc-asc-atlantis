#!/usr/bin/env bash

set -e

#################################
## Variables that control client
## functions and response parsing
#################################
: "${iAPI_HEALTH_CMD:="health"}"
: "${iAPI_HEALTH_FIELD:="status"}"
: "${iAPI_HEALTH_GOOD:="ok"}"

: "${iAPI_POST_VDS_CMD:="post vds"}"
: "${iAPI_GET_VDS_CMD:="get vds"}"
: "${iAPI_VDS_STATUS_FIELD:="status"}"
: "${iAPI_VDS_VD_UUID_FIELD:="vd_uuid"}"
: "${iAPI_VDS_CPV_UUID_FIELD:="cpv_uuid"}"
: "${iAPI_VDS_STATUS_PASSED:="accepted"}"
: "${iAPI_VDS_STATUS_TESTING:="pending"}"
: "${iAPI_VDS_STATUS_INVALID:="rejected"}"

: "${iAPI_POST_GP_CMD:="post gp"}"
: "${iAPI_GET_GP_CMD:="get gp"}"
: "${iAPI_GP_STATUS_FIELD:="status"}"
: "${iAPI_GP_GP_UUID_FIELD:="gp_uuid"}"
: "${iAPI_GP_STATUS_PASSED:="accepted"}"
: "${iAPI_GP_STATUS_BUILT:="accepted"}"
: "${iAPI_GP_STATUS_BUILDING:="pending"}"
: "${iAPI_GP_STATUS_INVALID:="rejected"}"

#################################
## Sanity checking /setup steps
#################################

# setup iAPI script invocation based on if it is found
# in the path or the local directory
SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
iAPI_SCRIPT="iapi_client.sh"
iAPI_CLI_COMMAND="${iAPI_SCRIPT}"
command -v "${iAPI_CLI_COMMAND}" >/dev/null || iAPI_CLI_COMMAND="${SCRIPT_DIR}/bin/${iAPI_SCRIPT}"

#################################
## Status / Health iAPI functions
#################################

# get iAPI health status field value
iapi_get_health_status_value() {
	# shellcheck disable=SC2086
	"${iAPI_CLI_COMMAND}" ${iAPI_HEALTH_CMD} 2>/dev/null | jq -r ".${iAPI_HEALTH_FIELD}" 2>/dev/null || true
}
export -f iapi_get_health_status_value

# does the iAPI health status field report a good status
iapi_status_good() {
	[[ $(iapi_get_health_status_value) == "${iAPI_HEALTH_GOOD}" ]]
}
export -f iapi_status_good

#################################
## VDS submission iAPI functions
#################################

# do VDS submission and return vd_uuid for a valid/accepted submission
iapi_post_vds_vd_uuid() {
	# shellcheck disable=SC2086
	"${iAPI_CLI_COMMAND}" ${iAPI_POST_VDS_CMD} "$@" 2>/dev/null | jq -r "select(.${iAPI_VDS_STATUS_FIELD}==\"${iAPI_VDS_STATUS_PASSED}\") | .${iAPI_VDS_VD_UUID_FIELD}" 2>/dev/null || true
}
export -f iapi_post_vds_vd_uuid

# do VDS submission GET and return status field
iapi_get_vds_status_value() {
	# shellcheck disable=SC2086
	"${iAPI_CLI_COMMAND}" ${iAPI_GET_VDS_CMD} "$@" 2>/dev/null | jq -r ".${iAPI_VDS_STATUS_FIELD}" 2>/dev/null || true
}
export -f iapi_get_vds_status_value

# do VDS submission GET and return cpv_uuid for a valid/accepted submission
iapi_get_vds_cpv_uuid() {
	# shellcheck disable=SC2086
	"${iAPI_CLI_COMMAND}" ${iAPI_GET_VDS_CMD} "$@" 2>/dev/null | jq -r "select(.${iAPI_VDS_STATUS_FIELD}==\"${iAPI_VDS_STATUS_PASSED}\") | .${iAPI_VDS_CPV_UUID_FIELD}" 2>/dev/null || true
}
export -f iapi_get_vds_cpv_uuid

__vds_submission_api_accepted() {
	declare -A VDS_STATUS_API_EVALUATION=(
		[internal_error]=false
		[${iAPI_VDS_STATUS_PASSED}]=true
		[${iAPI_VDS_STATUS_TESTING}]=true
		[${iAPI_VDS_STATUS_INVALID}]=true
	)
	"${VDS_STATUS_API_EVALUATION[${1:-internal_error}]:-${VDS_STATUS_API_EVALUATION[internal_error]}}"
}

# verify if returned status indicates submission made it through the API
iapi_vds_submission_api_accepted() {
	local -l vds_value
	vds_value=$(iapi_get_vds_status_value "$@")
	__vds_submission_api_accepted "${vds_value}"
}
export -f iapi_vds_submission_api_accepted

__vds_submission_not_rejected() {
	declare -A VDS_STATUS_NOT_REJECTED=(
		[default]=false
		[${iAPI_VDS_STATUS_PASSED}]=true
		[${iAPI_VDS_STATUS_TESTING}]=true
	)
	"${VDS_STATUS_NOT_REJECTED[${1:-default}]:-${VDS_STATUS_NOT_REJECTED[default]}}"
}

# verify if returned status indicates submission has not yet been marked as failed
iapi_vds_submission_not_rejected() {
	local -l vds_value
	vds_value=$(iapi_get_vds_status_value "$@")
	__vds_submission_api_accepted "${vds_value}" && __vds_submission_not_rejected "${vds_value}"
}
export -f iapi_vds_submission_not_rejected

__vds_submission_finished() {
	declare -A VDS_STATUS_FINISHED=(
		[default]=false
		[${iAPI_VDS_STATUS_PASSED}]=true
		[${iAPI_VDS_STATUS_INVALID}]=true
	)
	"${VDS_STATUS_FINISHED[${1:-default}]:-${VDS_STATUS_FINISHED[default]}}"
}

# verify if returned status indicates submission evaluation is completed
iapi_vds_submission_finished() {
	local -l vds_value
	vds_value=$(iapi_get_vds_status_value "$@")
	__vds_submission_api_accepted "${vds_value}" && __vds_submission_finished "${vds_value}"
}
export -f iapi_vds_submission_finished

__vds_submission_passed() {
	declare -A VDS_STATUS_PASSED=(
		[default]=false
		[${iAPI_VDS_STATUS_PASSED}]=true
	)
	"${VDS_STATUS_PASSED[${1:-default}]:-${VDS_STATUS_PASSED[default]}}"
}

# verify if returned status indicates submission scored/passed
iapi_vds_submission_passed() {
	local -l vds_value
	vds_value=$(iapi_get_vds_status_value "$@")
	__vds_submission_api_accepted "${vds_value}" && __vds_submission_passed "${vds_value}"
}
export -f iapi_vds_submission_passed

#################################
## GP submission iAPI functions
#################################

# do GP submission and return gp_uuid for a valid/accepted submission
iapi_post_gp_gp_uuid() {
	# shellcheck disable=SC2086
	"${iAPI_CLI_COMMAND}" ${iAPI_POST_GP_CMD} "$@" 2>/dev/null | jq -r "select(.${iAPI_GP_STATUS_FIELD}==\"${iAPI_GP_STATUS_PASSED}\") | .${iAPI_GP_GP_UUID_FIELD}" 2>/dev/null || true
}
export -f iapi_post_gp_gp_uuid

# get iAPI get GP submission status
iapi_get_gp_status_value() {
	# shellcheck disable=SC2086
	"${iAPI_CLI_COMMAND}" ${iAPI_GET_GP_CMD} "$@" 2>/dev/null | jq -r ".${iAPI_GP_STATUS_FIELD}" 2>/dev/null || true
}
export -f iapi_get_gp_status_value

__gp_submission_api_accepted() {
	declare -A GP_STATUS_API_EVALUATION=(
		[internal_error]=false
		[${iAPI_GP_STATUS_BUILT}]=true
		[${iAPI_GP_STATUS_BUILDING}]=true
		[${iAPI_GP_STATUS_INVALID}]=true
	)
	"${GP_STATUS_API_EVALUATION[${1:-internal_error}]:-${GP_STATUS_API_EVALUATION[internal_error]}}"
}

# verify if returned status indicates submission made it through the API
iapi_gp_submission_api_accepted() {
	local -l gp_value
	gp_value=$(iapi_get_gp_status_value "$@")
	__gp_submission_api_accepted "${gp_value}"
}
export -f iapi_gp_submission_api_accepted

__gp_submission_not_rejected() {
	declare -A GP_STATUS_NOT_REJECTED=(
		[default]=false
		[${iAPI_GP_STATUS_BUILT}]=true
		[${iAPI_GP_STATUS_BUILDING}]=true
	)
	"${GP_STATUS_NOT_REJECTED[${1:-default}]:-${GP_STATUS_NOT_REJECTED[default]}}"
}

# verify if returned status indicates submission has not yet been marked as failed
iapi_gp_submission_not_rejected() {
	local -l gp_value
	gp_value=$(iapi_get_gp_status_value "$@")
	__gp_submission_api_accepted "${gp_value}" && __gp_submission_not_rejected "${gp_value}"
}
export -f iapi_gp_submission_not_rejected

__gp_submission_finished() {
	declare -A GP_STATUS_FINISHED=(
		[default]=false
		[${iAPI_GP_STATUS_BUILT}]=true
		[${iAPI_GP_STATUS_INVALID}]=true
	)
	"${GP_STATUS_FINISHED[${1:-default}]:-${GP_STATUS_FINISHED[default]}}"
}

# verify if returned status indicates submission evaluation is completed
iapi_gp_submission_finished() {
	local -l gp_value
	gp_value=$(iapi_get_gp_status_value "$@")
	__gp_submission_api_accepted "${gp_value}" && __gp_submission_finished "${gp_value}"
}
export -f iapi_gp_submission_finished

__gp_submission_built() {
	declare -A GP_STATUS_BUILT=(
		[default]=false
		[${iAPI_GP_STATUS_BUILT}]=true
	)
	"${GP_STATUS_BUILT[${1:-default}]:-${GP_STATUS_BUILT[default]}}"
}

# verify if returned status indicates submission built
iapi_gp_submission_built() {
	local -l gp_value
	gp_value=$(iapi_get_gp_status_value "$@")
	__gp_submission_api_accepted "${gp_value}" && __gp_submission_built "${gp_value}"
}
export -f iapi_gp_submission_built
