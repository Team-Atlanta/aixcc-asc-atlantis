#! /bin/bash

MESSAGE=${1}

export VAPI_DATABASE_PATH="memory"

CONTAINER=vapi-migrations

function kill_container() {
	# if the container is there, stop and remove it
	docker rm -f ${CONTAINER}
}
# if this script exits, shut down the container
trap kill_container EXIT

sleep 2

poetry run alembic upgrade head
poetry run alembic revision --autogenerate -m "${MESSAGE}"
