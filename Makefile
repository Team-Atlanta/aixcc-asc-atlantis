ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
THIS_FILE := $(lastword $(MAKEFILE_LIST))
DOCKER_COMPOSE_FILE = $(ROOT_DIR)/compose.yaml
DOCKER_COMPOSE_LOCAL_OVERRIDES = $(ROOT_DIR)/compose_local_overrides.yaml
DOCKER_COMPOSE_LOCAL_ARGS = -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_LOCAL_OVERRIDES) --profile development
DOCKER_COMPOSE_LOCAL_MOCK_CRS_ARGS = -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_LOCAL_OVERRIDES) --profile mock-crs

# variables that control the volumes
export UID=$(shell id -u)
export GID=$(shell id -g)
HOST_CRS_SCRATCH = $(ROOT_DIR)/crs_scratch
HOST_DIND_CACHE = $(ROOT_DIR)/dind_cache
HOST_CAPI_LOGS = $(ROOT_DIR)/capi_logs

LOCAL_K8S_BASE = $(ROOT_DIR)/sandbox/kustomize/base
LOCAL_K8S_RESOURCES = $(ROOT_DIR)/.k8s


# variables that control the CP repos
HOST_CP_ROOT_DIR = $(ROOT_DIR)/cp_root
CP_CONFIG_FILE ?= $(ROOT_DIR)/cp_config/cp_config.yaml

# location of local env file
HOST_ENV_FILE = $(ROOT_DIR)/sandbox/env

# Check for required files that will error out elsewhere if not present
ENV_FILES_PRESENT = $(wildcard $(HOST_ENV_FILE))
INVALID_GITHUB_ENV_VARS = $(shell grep -E '^GITHUB_(TOKEN|USER)=(<REPLACE_WITH.*|)$$' <$(HOST_ENV_FILE))
GITHUB_ENV_VAR_COUNT = $(shell grep -E '^GITHUB_(TOKEN|USER)' -c <$(HOST_ENV_FILE))

ifeq (,$(ENV_FILES_PRESENT))
$(warning No env file found at $(HOST_ENV_FILE).  Please copy & fill out sandbox/example.env and try again.  See the README and the file's comments for details.)
else ifneq (,$(INVALID_GITHUB_ENV_VARS))
$(warning Uninitialized GitHub credentials in $(HOST_ENV_FILE).  In order for make up to work, these need to be set to values that can pull containers and clone repos.)
else ifneq (2,$(GITHUB_ENV_VAR_COUNT))
$(warning Not all GitHub credentials are set in $(HOST_ENV_FILE).  In order for make up to work, these need to be set to values that can pull containers and clone repos.  Check sandbox/example.env and README.md for what these are and how to set them.)
endif

ifeq (,$(wildcard $(CP_CONFIG_FILE)))
$(error Required file not found: $(CP_CONFIG_FILE))
endif

# Check for required executables (dependencies)
__UNUSED_REQUIRED_EXE = yq docker kompose
__UNUSED_EVAL_EXES := $(foreach exe,$(__UNUSED_REQUIRED_EXE), \
	$(if $(shell command -v $(exe)),,$(warning Required executable not in PATH: $(exe))))

# Check yq version
__UNUSED_YQ_REQUIRED_MAJOR_VERSION ?= 4
__UNUSED_YQ_ACTUAL_MAJOR_VERSION = $(shell yq --version | grep -o "version v.*" | grep -Eo '[0-9]+(\.[0-9]+)+' | cut -f1 -d'.')
ifneq ($(__UNUSED_YQ_REQUIRED_MAJOR_VERSION),$(__UNUSED_YQ_ACTUAL_MAJOR_VERSION))
$(error Unexpected major version of 'yq'. Expected: $(__UNUSED_YQ_REQUIRED_MAJOR_VERSION), Actual: $(__UNUSED_YQ_ACTUAL_MAJOR_VERSION)))
endif

# Determine CP repo targets
CP_TARGETS_DIRS = $(shell yq -r '.cp_targets | keys | .[]' $(CP_CONFIG_FILE))
CP_MAKE_TARGETS = $(addprefix $(HOST_CP_ROOT_DIR)/.pulled_, $(subst :,_colon_, $(subst /,_slash_, $(CP_TARGETS_DIRS))))

.PHONY: help build up start down destroy stop restart logs logs-crs logs-litellm logs-iapi ps crs-shell litellm-shell cps/clean cps computed-env clear-dind-cache env-file-required github-creds-required k8s k8s/clean k8s/kustomize/development k8s/kustomize/competition install k8s/development k8s/competition

help: ## Display available targets and their help strings
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_/-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(THIS_FILE) | sort

env-file-required:
	@if [ -z "$(ENV_FILES_PRESENT)" ]; then exit 1; fi

github-creds-required: env-file-required
	@if [ -n "$(INVALID_GITHUB_ENV_VARS)" ]; then exit 1; fi
	@if [ "$(GITHUB_ENV_VAR_COUNT)" -lt 2 ]; then exit 1; fi

build-no-cache: ## Build the project without pulling images
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) build $(c)

build: ## Build the project, pull images if available
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) build --pull $(c)

computed-env: env-file-required
	@sed -i '/CAPI_AUTH_HEADER=*/d' sandbox/env
	$(eval include sandbox/env)
	@printf 'CAPI_AUTH_HEADER="Basic ' >> sandbox/env
	@printf "%s:%s" "${CAPI_ID}" "${CAPI_TOKEN}" | base64 | tr -d '\n' >> sandbox/env
	@printf '"' >> sandbox/env

local-volumes:
	mkdir -p $(HOST_CP_ROOT_DIR) $(HOST_CRS_SCRATCH) $(HOST_DIND_CACHE) $(HOST_CAPI_LOGS)

up: github-creds-required local-volumes cps computed-env ## Start containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) up -d $(c)

up-attached: github-creds-required cps computed-env ## Start containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) up --build --abort-on-container-exit $(c)

show-config:
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) config $(c)

mock-crs/up-attached: github-creds-required cps computed-env ## Start containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_MOCK_CRS_ARGS) up --build --abort-on-container-exit $(c)

start: github-creds-required ## Start containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) start $(c)

down: ## Stop and remove containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) down --remove-orphans $(c)

destroy: clear-dind-cache ## Stop and remove containers with volumes
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) down --volumes --remove-orphans $(c)

clear-dind-cache: ## Clears out DIND cached artifacts
	@echo "Deleting the docker-in-docker cache folder, which requires sudo.  You will be prompted for your password."
	@sudo rm -rf $(HOST_DIND_CACHE)

stop: ## Stop containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) stop $(c)

restart: github-creds-required computed-env ## Restart containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) stop $(c)
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) up -d $(c)

logs: ## Show logs for containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) logs --tail=100 -f $(c)

logs-nofollow: ## Show logs for containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) logs $(c)

logs-crs: ## Show logs for crs container
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) logs --tail=100 -f crs

logs-crs-nofollow: ## Show logs for crs container
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) logs crs

logs-litellm: ## Show logs for litellm container
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) logs --tail=100 -f litellm

logs-capi: ## Show logs for capi container
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) logs --tail=100 -f capi

logs-iapi: ## Show logs for iapi container
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) logs --tail=100 -f iapi

logs-capi-audit: ## Watch the cAPI's audit log
	@tail -f $(HOST_CAPI_LOGS)/audit.log

ps: ## List containers
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) ps

crs-shell: ## Access the crs shell
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) exec crs /bin/bash

litellm-shell: ## Access the litellm shell
	@docker compose $(DOCKER_COMPOSE_LOCAL_ARGS) exec litellm /bin/bash

## Internal target to clone and pull the CP source for each CP repo
$(HOST_CP_ROOT_DIR)/.pulled_%:
	$(eval REVERT_CP_TARGETS_DIRS_ESCAPE_STR=$(subst _colon_,:,$(subst _slash_,/,$*)))
	$(eval CP_ROOT_REPO_SUBDIR=$(@D)/$(REVERT_CP_TARGETS_DIRS_ESCAPE_STR))
	@$(RM) -r $(CP_ROOT_REPO_SUBDIR)
	@mkdir -p $(CP_ROOT_REPO_SUBDIR)
	@yq -r '.cp_targets["$(REVERT_CP_TARGETS_DIRS_ESCAPE_STR)"].url' $(CP_CONFIG_FILE) | \
		xargs -I {} git clone {} $(CP_ROOT_REPO_SUBDIR)
	@yq -r '.cp_targets["$(REVERT_CP_TARGETS_DIRS_ESCAPE_STR)"] | .ref // "main"' $(CP_CONFIG_FILE) | \
		xargs -I {} sh -c \
			"git -C $(CP_ROOT_REPO_SUBDIR) fetch --depth 1 origin {}; \
			git -C $(CP_ROOT_REPO_SUBDIR) checkout --quiet {};"
	make -C $(CP_ROOT_REPO_SUBDIR) cpsrc-prepare
	@touch $@

cps: local-volumes $(CP_MAKE_TARGETS) ## Clone CP repos

cps/clean: ## Clean up the cloned CP repos
	@rm -rf $(HOST_CP_ROOT_DIR)

loadtest: local-volumes computed-env ## Run k6 load tests
	@docker compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_LOCAL_OVERRIDES) --profile loadtest up --exit-code-from test --build $(c)
loadtest/destroy: ## Stop and remove containers with volumes
	@docker compose -f $(DOCKER_COMPOSE_FILE) -f $(DOCKER_COMPOSE_LOCAL_OVERRIDES) --profile loadtest down --volumes --remove-orphans $(c)

k8s: k8s/clean k8s/development k8s/kustomize/development build ## Generates helm chart locally for the development profile for kind testing, etc. build is called for local image generation
	@docker pull ghcr.io/aixcc-sc/capi:v2.1.9
	@docker pull ghcr.io/berriai/litellm-database:main-v1.35.10
	@docker pull nginx:1.25.5
	@docker pull docker:24-dind
	@docker pull postgres:16.2-alpine3.19
	@docker pull ghcr.io/aixcc-sc/crs-sandbox/mock-crs:v2.0.0
	@docker pull curlimages/curl:8.8.0
	@docker pull ghcr.io/aixcc-sc/load-cp-images:v0.0.11
	@helm repo add longhorn https://charts.longhorn.io
	@helm repo update
	@helm install --kube-context crs longhorn longhorn/longhorn --namespace longhorn-system --create-namespace --set defaultSetting.defaultStorageClass=true
	@kubectl create --context=crs secret docker-registry regcred --docker-server=https://ghcr.io --docker-username=oauth2 --docker-password=$(GITHUB_TOKEN)
	@kubectl apply --context=crs -f $(LOCAL_K8S_RESOURCES)

k8s/clean:
	@rm -rf $(LOCAL_K8S_BASE)/resources.yaml
	@rm -rf $(LOCAL_K8S_RESOURCES)

install:
	@echo "Updating package list"
	sudo apt-get update

	@echo "Installing Docker Compose"
	sudo curl -L "https://github.com/docker/compose/releases/download/v2.26.1/docker-compose-$$(uname -s)-$$(uname -m)" -o /usr/local/bin/docker-compose
	sudo chmod +x /usr/local/bin/docker-compose

	@echo "Setting file limits"
	echo -e "* soft nofile 65536\n* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
	echo "fs.file-max = 65536" | sudo tee -a /etc/sysctl.conf
	sudo sysctl -p
	echo "DefaultLimitNOFILE=65536" | sudo tee -a /etc/systemd/system.conf
	echo "DefaultLimitNOFILE=65536" | sudo tee -a /etc/systemd/user.conf
	sudo systemctl daemon-reload

	@echo "Installing required packages"
	sudo apt-get install -y open-iscsi nfs-common

	@echo "Installing K3s with custom configuration"
	curl -sfL https://get.k3s.io | sh -

	@echo "Setting up kubeconfig"
	mkdir -p ~/.kube
	sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
	sudo chown "$${USER}" ~/.kube/config
	@echo "Configuring custom Kubernetes context 'crs'"
	kubectl config rename-context default crs

	@echo "Getting Kubernetes nodes"
	kubectl get nodes --context=crs

	@echo "Installing mise"
	curl https://mise.jdx.dev/install.sh | sh
	mise install
	echo "eval \"$$(mise activate bash)\"" >> "$${HOME}/.bashrc"

k8s/k3s/clean:
	@if [ -f /usr/local/bin/k3s-uninstall.sh ]; then \
		sudo /usr/local/bin/k3s-uninstall.sh \
	else \
		echo "K3S Uninstall file does not exist...skipping"; \
	fi

k8s/development: github-creds-required k8s/clean
	@mkdir -p $(LOCAL_K8S_RESOURCES)
	@mkdir -p $(LOCAL_K8S_BASE)
	@COMPOSE_FILE="$(ROOT_DIR)/compose.yaml $(ROOT_DIR)/kompose_development_overrides.yaml" kompose convert --service-group-mode=label --profile development --out $(LOCAL_K8S_BASE)/resources.yaml
	@cp cp_config/cp_config.yaml $(LOCAL_K8S_BASE)/cp_config.yaml

k8s/kustomize/development:
	@kustomize build $(ROOT_DIR)/sandbox/kustomize/development -o $(LOCAL_K8S_RESOURCES)/resources.yaml

k8s/competition: env-file-required k8s/clean ## Generates the competition k8s resources for use during the evaluation window and competition
	@mkdir -p $(LOCAL_K8S_RESOURCES)
	@mkdir -p $(LOCAL_K8S_BASE)
	@COMPOSE_FILE="$(ROOT_DIR)/compose.yaml $(ROOT_DIR)/kompose_competition_overrides.yaml" kompose convert --service-group-mode=label --profile competition --out $(LOCAL_K8S_BASE)/resources.yaml
	@cp cp_config/cp_config.yaml $(LOCAL_K8S_BASE)/cp_config.yaml
	@if grep -qr "$(RELEASE_TAG)" $(LOCAL_K8S_BASE); then \
		echo "RELEASE_TAG $(RELEASE_TAG) was found in $(LOCAL_K8S_BASE)"; \
	else \
		echo "[+] WARNING: var RELEASE_TAG $(RELEASE_TAG) not found. Specify this tag in compose.yaml  for each of your service container images to be tagged with your release version"; \
		echo "[+] 	Please make sure to add :\${RELEASE_TAG-v1.0.0} where v1.0.0 is the fallback default to your CRS containers so they automatically update on release"; \
	fi

k8s/kustomize/competition:
	@kustomize build $(ROOT_DIR)/sandbox/kustomize/competition -o $(LOCAL_K8S_RESOURCES)/resources.yaml

clean-volumes: clear-dind-cache
	rm -rf $(HOST_CP_ROOT_DIR) $(HOST_CRS_SCRATCH) $(HOST_CAPI_LOGS)

clean: cps/clean k8s/clean down clear-dind-cache

force-reset: ## Remove all local docker containers, networks, volumes, and images
	@docker system prune --all
