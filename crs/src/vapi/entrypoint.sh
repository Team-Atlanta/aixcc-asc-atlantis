#! /bin/bash

VAPI_PORT=18080

set -e

cd competition_api && poetry run alembic upgrade head && cd -

VAPI_HOSTNAME=http://localhost:$VAPI_PORT python3 gp_requests_update_requester/main.py &

poetry run uvicorn competition_api.main:app --host 0.0.0.0 --port $VAPI_PORT --workers ${WEB_CONCURRENCY:-4}
