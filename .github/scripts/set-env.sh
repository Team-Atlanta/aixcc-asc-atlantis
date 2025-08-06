#! /bin/sh

set -e

ENV_FILE=${ENV_FILE:-sandbox/env}
KEY=$1
VALUE=$2

if [ -n "$VALUE" ]; then
	echo "Setting ${KEY} in ${ENV_FILE}"
	sed -i "s/${KEY}=.*/${KEY}=${VALUE}/" "$ENV_FILE"
else
	echo "Not setting ${KEY} because value was empty"
fi
