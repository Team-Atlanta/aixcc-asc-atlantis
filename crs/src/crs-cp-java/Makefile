ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

SHELLCHECK_SCRIPTS:= \
	$(shell find $(ROOT_DIR) -type f -name "*.sh" -not -path "./.git*")

.PHONY: help lint
.DEFAULT_GOAL := lint

# Define a reusable function to execute a command
define run_and_capture_output
	@{ \
	echo "[-] Running $(1) ..."; \
	set -e; \
	tmpfile=$$(mktemp); \
	trap "rm -f $$tmpfile" EXIT; \
	$(1) >$$tmpfile 2>&1 || { \
		cat $$tmpfile; \
		echo "[!] $(1) returned with error"; \
		exit 1; \
	}; \
	rm -f $$tmpfile; \
	echo "[-] Done $(1) "; \
	}
endef

help: ## Show all Makefile targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'

lint_shell: $(SHELLCHECK_SCRIPTS) ## lint the shell scripts with shellcheck
	@shellcheck $^

lint: lint_shell ## lint everything

test_iapi: $(ROOT_DIR)/test/iapi_function_tests.sh ## Run iAPI client and wrapper test
	$<

_test_java_harness_processor: $(ROOT_DIR)/test/java_harness_processor_tests.sh ## Run java harness processor tests
	$<

_test_java_dict_generator: $(ROOT_DIR)/test/java_dict_generator_tests.sh ## Run java_dict_generator tests
	$(call run_and_capture_output, $<)

_test_jazzer: $(ROOT_DIR)/test/jazzer_tests.sh ## Run jazzer tests
	$(call run_and_capture_output, $<)

_test_jenkins: $(ROOT_DIR)/test/jenkins_tests.sh ## Run jenkins tests
	$(call run_and_capture_output, $<)

_test_joern: $(ROOT_DIR)/test/joern_api_test.sh ## Run joern api tests
	#$(call run_and_capture_output, $<)
	$<

prepare: ## Prepare the test environment
	@echo "[-] Preparing test environment..."
	$(ROOT_DIR)/run.py --cp-root $(AIXCC_CP_ROOT) --cmd prepare
	@echo "[-] Preparing test environment Done"

test: prepare _test_jenkins _test_jazzer _test_java_dict_generator _test_joern 

test_java_harness_processor: prepare _test_java_harness_processor ## Run java harness processor tests

test_jenkins: prepare _test_jenkins

test_jazzer: prepare _test_jazzer

test_java_dict_generator: prepare _test_java_dict_generator

test_joern: prepare _test_joern
