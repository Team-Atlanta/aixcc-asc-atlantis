ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

SHELLCHECK_SCRIPTS:= \
	$(shell find $(ROOT_DIR) -type f -name "*.sh" -not -path "./.git*")

.PHONY: help lint
.DEFAULT_GOAL := lint

help: ## Show all Makefile targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'

lint_shell: $(SHELLCHECK_SCRIPTS) ## lint the shell scripts with shellcheck
	@shellcheck $^

lint: lint_shell ## lint everything

test_iapi: $(ROOT_DIR)/test/iapi_function_tests.sh ## Run iAPI client and wrapper test
	$<

test: test_iapi ## Run tests
