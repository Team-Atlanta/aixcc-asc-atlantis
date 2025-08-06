MODULES=competition_api tests
ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# variables that control the volumes
HOST_CAPI_LOGS = $(ROOT_DIR)/capi_logs
HOST_CRS_SCRATCH = $(ROOT_DIR)/crs_scratch
export AUDIT_LOG = $(HOST_CAPI_LOGS)/audit.log

# variables the control the CP repos
HOST_CP_ROOT_DIR = $(ROOT_DIR)/cp_root

VOLUMES = $(HOST_CAPI_LOGS) $(HOST_CRS_SCRATCH) $(HOST_CP_ROOT_DIR)

export WEB_CONCURRENCY=4

.PHONY: format sec lint build run test up down e2e loadtest

format:
	poetry run isort $(MODULES)
	poetry run black $(MODULES)
	prettier --write "./**/*.js"

sec:
	poetry run bandit $(MODULES)
	poetry run safety check $(MODULES)

lint:
	RC=0; \
	poetry run pylint $(MODULES) || RC=1; \
	poetry run black --check $(MODULES) || RC=1; \
	poetry run isort --check $(MODULES) || RC=1; \
	poetry run mypy $(MODULES) || RC=1; \
	exit $$RC

local-volumes:
	mkdir -p $(VOLUMES)
	chmod 777 $(VOLUMES)

build:
	@docker build . -t capi

run: build
	docker run -it capi

test:
	poetry run pytest --cov=competition_api --cov-report term-missing:skip-covered ${TESTS}

compose-build:
	docker compose build

compose-build-loadtest:
	docker compose --profile loadtest build

up: local-volumes compose-build
	docker compose up

down:
	docker compose down

down-volumes:
	docker compose down -v

mock-cp: local-volumes
	rm -rf $(HOST_CP_ROOT_DIR)/$@
	git clone git@github.com:team-atlanta/mock-cp.git $(HOST_CP_ROOT_DIR)/$@
	sed -i '/DOCKER_IMAGE_NAME=.*/d' $(HOST_CP_ROOT_DIR)/$@/.env.project
	cd $(HOST_CP_ROOT_DIR)/$@ && make cpsrc-prepare

linux-cp: local-volumes
	rm -rf $(HOST_CP_ROOT_DIR)/$@
	git clone git@github.com:team-atlanta/challenge-001-linux-cp.git $(HOST_CP_ROOT_DIR)/$@
	sed -i '/DOCKER_IMAGE_NAME=.*/d' $(HOST_CP_ROOT_DIR)/$@/.env.project
	sed -i '/docker_image: challenge-001-linux-cp/c\docker_image: ghcr.io/team-atlanta/challenge-001-linux-cp:v1338' $(HOST_CP_ROOT_DIR)/$@/project.yaml
	cd $(HOST_CP_ROOT_DIR)/$@ && make cpsrc-prepare

jenkins-cp: local-volumes
	rm -rf $(HOST_CP_ROOT_DIR)/$@
	git clone git@github.com:team-atlanta/asc-challenge-002-jenkins-cp.git $(HOST_CP_ROOT_DIR)/$@
	sed -i '/DOCKER_IMAGE_NAME=.*/d' $(HOST_CP_ROOT_DIR)/$@/.env.project
	cd $(HOST_CP_ROOT_DIR)/$@ && make cpsrc-prepare

all-cp: mock-cp linux-cp jenkins-cp

clean-volumes:
	rm -rf $(VOLUMES)
	rm -f loadtest/loadtest_config.yaml

clean: down-volumes clean-volumes

e2e: clean clean-volumes local-volumes mock-cp compose-build
	:>$(AUDIT_LOG)
	WEB_CONCURRENCY=4 docker compose up -d
	cd e2e && ./run.sh; docker compose down
	cat $(AUDIT_LOG)

loadtest/loadtest_config.yaml:
	@printf -- "---\n" > $@
	@printf "auth:\n" >> $@
	@printf "  preload:\n" >> $@
	@for i in {1..100}; do printf "    %s: secret\n" $$(uuidgen) >> $@; done
	@printf "database:\n" >> $@
	@printf "  pool:\n" >> $@
	@printf "    size: 450\n" >> $@

loadtest: clean loadtest/loadtest_config.yaml mock-cp
	@docker compose --profile loadtest -f compose.yaml -f loadtest/compose_overrides.yaml up --force-recreate --exit-code-from loadtest --build
