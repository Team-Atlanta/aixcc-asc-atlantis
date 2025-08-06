#!/usr/bin/env bash

set -eo pipefail

# get script's file name for usage print statements
SCRIPT_FILE="$(basename "${BASH_SOURCE[0]}")"

# set target hostname based on expect iAPI environment variable
API_HOSTNAME=${AIXCC_API_HOSTNAME:-"localhost:8080"}
: "${API_HEALTH_PATH:="health"}"
: "${API_SUBMISSION_VDS_PATH:="submission/vds"}"
: "${API_SUBMISSION_GP_PATH:="submission/gp"}"

# default curl command arguments
: "${CURL_EXTRA_ARGS:="--silent --show-error"}"

#################################
## Utility functions
#################################

# print warning
warn() {
	echo "$*" >&2
}

# print the script's main usage menu
print_toplevel_usage() {
	warn "Usage: ${SCRIPT_FILE} post|get|health|help"
	warn
	warn "Make HTTP requests (via curl) to the AIxCC internal API (iAPI)."
	warn "The API endpoint is set with the environment variable AIXCC_API_HOSTNAME."
	warn "The raw output from curl is returned to the caller."
	warn
	warn "The current value of the API endpoint is: ${API_HOSTNAME}"
	warn
	warn "Subcommands:"
	warn "  post       Perform HTTP Post on iAPI endpoints (See 'post' submenu)"
	warn "  get        Perform HTTP Get on iAPI endpoints (See 'get' submenu)"
	warn "  health     Retrieve the iAPI interface health status"
	warn "  help       Show this help message and exit"
	exit 1
}

# print the post subcommand usage menu
print_post_usage() {
	warn "Usage: ${SCRIPT_FILE} post vds|gp|help [<CURL_ARGS>]"
	warn
	warn "Make HTTP POST requests (via curl) to the AIxCC internal API (iAPI)."
	warn "The API endpoint is set with the environment variable AIXCC_API_HOSTNAME."
	warn
	warn "Subcommands:"
	warn "  vds     Post a VDS submission to ${API_HOSTNAME}/${API_SUBMISSION_VDS_PATH}"
	warn "  gp      Post a GP submission to ${API_HOSTNAME}/${API_SUBMISSION_GP_PATH}"
	warn "  help    Show this help message and exit"
	warn
	warn "Options:"
	warn " <CURL_ARGS>  Optional arguments passed directly to curl"
	exit 1
}

# print the get subcommand usage menu
print_get_usage() {
	warn "Usage: ${SCRIPT_FILE} get vds|gp|help <uuid> [<CURL_ARGS>]"
	warn
	warn "Make HTTP GET requests (via curl) to the AIxCC internal API (iAPI)."
	warn "The API endpoint is set with the environment variable AIXCC_API_HOSTNAME."
	warn
	warn "Subcommands:"
	warn "  vds          Get a VDS submission status via ${API_HOSTNAME}/${API_SUBMISSION_VDS_PATH}"
	warn "  gp           Get a GP submission status via ${API_HOSTNAME}/${API_SUBMISSION_GP_PATH}"
	warn "  help         Show this help message and exit"
	warn
	warn "Arguments:"
	warn "  <uuid>       VD_UUID or GP_UUID to query"
	warn
	warn "Options:"
	warn "  <CURL_ARGS>  Optional arguments passed directly to curl"
	exit 1
}

#################################
## Subcommand functions
#################################

# call curl with the passed options and arguments
curl_generic_with_args() {
	# call curl with arguments (script exits/returns here)
	# shellcheck disable=SC2086
	curl \
		${CURL_EXTRA_ARGS} \
		--header "Content-Type: application/json" \
		--header "accept: application/json" \
		"$@"
}

# make VDS submission
post_vds() {
	shift
	curl_generic_with_args --request POST "${API_HOSTNAME}/${API_SUBMISSION_VDS_PATH}/" "$@"
}

# make a GP submission
post_gp() {
	shift
	curl_generic_with_args --request POST "${API_HOSTNAME}/${API_SUBMISSION_GP_PATH}/" "$@"
}

# handler of post subcommand
post() {
	shift

	# calls post subcommand function from declared array
	"${POST_SUB_COMMANDS[${1:-help}]:-${POST_SUB_COMMANDS[help]}}" "$@"
}

# array of post subcommand secondary commands
declare -A POST_SUB_COMMANDS=(
	[help]=print_post_usage
	[vds]=post_vds
	[gp]=post_gp
)

# make VDS submission status GET request
get_vds() {
	shift

	local uuid_val="${1}"
	[[ -n "${uuid_val}" ]] || {
		warn "Missing <uuid> argument"
		print_get_usage
	}
	shift

	curl_generic_with_args --request GET "${API_HOSTNAME}/${API_SUBMISSION_VDS_PATH}/${uuid_val}" "$@"
}

# make GP submission status GET request
get_gp() {
	shift

	local uuid_val="${1}"
	[[ -n "${uuid_val}" ]] || {
		warn "Missing <uuid> argument"
		print_get_usage
	}
	shift

	curl_generic_with_args --request GET "${API_HOSTNAME}/${API_SUBMISSION_GP_PATH}/${uuid_val}" "$@"
}

# handler for get subcommand
get() {
	shift

	# calls get subcommand function from declared array
	"${GET_SUB_COMMANDS[${1:-help}]:-${GET_SUB_COMMANDS[help]}}" "$@"
}

# array of get subcommand secondary commands
declare -A GET_SUB_COMMANDS=(
	[help]=print_get_usage
	[vds]=get_vds
	[gp]=get_gp
)

# get health endpoint data from API
health() {
	shift
	curl_generic_with_args --request GET "${API_HOSTNAME}/${API_HEALTH_PATH}/" "$@"
}

# array of top-level command handlers
declare -A MAIN_COMMANDS=(
	[help]=print_toplevel_usage
	[post]=post
	[get]=get
	[health]=health
)

#################################
## Main script code starts here
#################################

# check hostname variable isn't empty
if [[ -z "${API_HOSTNAME}" ]]; then
	warn "WARNING: hostname variable is not set. Inspect environment variable AIXCC_API_HOSTNAME."
fi

# look for needed commands
REQUIRED_COMMANDS="curl"
for c in ${REQUIRED_COMMANDS}; do
	command -v "${c}" >/dev/null || warn "WARNING: needed executable (${c}) not found in PATH"
done

# call subcommand function from declared array
"${MAIN_COMMANDS[${1:-help}]:-${MAIN_COMMANDS[help]}}" "$@"
